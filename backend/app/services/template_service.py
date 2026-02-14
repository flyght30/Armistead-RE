import logging
from datetime import timedelta
from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.milestone_template import MilestoneTemplate, MilestoneTemplateItem
from app.models.milestone import Milestone
from app.models.transaction import Transaction
from app.schemas.milestone_template import (
    MilestoneTemplateCreate,
    MilestoneTemplateUpdate,
    MilestoneTemplateResponse,
    MilestoneTemplateListResponse,
    ApplyTemplateRequest,
    ApplyTemplateResponse,
    SkippedMilestone,
)

logger = logging.getLogger(__name__)


async def list_templates(
    db: AsyncSession,
    state_code: Optional[str] = None,
    financing_type: Optional[str] = None,
    representation_side: Optional[str] = None,
) -> List[MilestoneTemplateListResponse]:
    """List templates with optional filtering."""
    stmt = select(MilestoneTemplate).where(MilestoneTemplate.is_active == True)

    if state_code:
        stmt = stmt.where(MilestoneTemplate.state_code == state_code.upper())
    if financing_type:
        stmt = stmt.where(MilestoneTemplate.financing_type == financing_type.lower())
    if representation_side:
        stmt = stmt.where(MilestoneTemplate.representation_side == representation_side.lower())

    stmt = stmt.options(selectinload(MilestoneTemplate.items))
    result = await db.execute(stmt)
    templates = result.scalars().all()

    responses = []
    for t in templates:
        resp = MilestoneTemplateListResponse.model_validate(t)
        resp.item_count = len(t.items)
        responses.append(resp)
    return responses


async def get_template(template_id: UUID, db: AsyncSession) -> MilestoneTemplateResponse:
    """Get a single template with all items."""
    stmt = (
        select(MilestoneTemplate)
        .where(MilestoneTemplate.id == template_id)
        .options(selectinload(MilestoneTemplate.items))
    )
    result = await db.execute(stmt)
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return MilestoneTemplateResponse.model_validate(template)


async def create_template(
    template_create: MilestoneTemplateCreate,
    db: AsyncSession,
    created_by: Optional[UUID] = None,
) -> MilestoneTemplateResponse:
    """Create a new milestone template with items."""
    template = MilestoneTemplate(
        name=template_create.name,
        state_code=template_create.state_code.upper(),
        financing_type=template_create.financing_type.lower(),
        representation_side=template_create.representation_side.lower(),
        description=template_create.description,
        is_default=False,
        created_by=created_by,
    )
    db.add(template)
    await db.flush()  # Get the template ID

    for item_data in template_create.items:
        item = MilestoneTemplateItem(
            template_id=template.id,
            type=item_data.type,
            title=item_data.title,
            day_offset=item_data.day_offset,
            offset_reference=item_data.offset_reference,
            responsible_party_role=item_data.responsible_party_role,
            reminder_days_before=item_data.reminder_days_before,
            is_conditional=item_data.is_conditional,
            condition_field=item_data.condition_field,
            condition_not_value=item_data.condition_not_value,
            sort_order=item_data.sort_order,
        )
        db.add(item)

    await db.commit()
    await db.refresh(template, ["items"])
    return MilestoneTemplateResponse.model_validate(template)


async def update_template(
    template_id: UUID,
    template_update: MilestoneTemplateUpdate,
    db: AsyncSession,
) -> MilestoneTemplateResponse:
    """Update a template's metadata."""
    template = await db.get(MilestoneTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    update_data = template_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)

    await db.commit()
    stmt = (
        select(MilestoneTemplate)
        .where(MilestoneTemplate.id == template_id)
        .options(selectinload(MilestoneTemplate.items))
    )
    result = await db.execute(stmt)
    template = result.scalar_one()
    return MilestoneTemplateResponse.model_validate(template)


async def apply_template(
    transaction_id: UUID,
    request: ApplyTemplateRequest,
    db: AsyncSession,
) -> ApplyTemplateResponse:
    """Apply a milestone template to a transaction, creating milestones with computed dates."""
    # Get the transaction
    transaction = await db.get(Transaction, transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Get the template with items
    stmt = (
        select(MilestoneTemplate)
        .where(MilestoneTemplate.id == request.template_id)
        .options(selectinload(MilestoneTemplate.items))
    )
    result = await db.execute(stmt)
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Update transaction dates
    transaction.contract_execution_date = request.contract_execution_date
    if request.closing_date:
        transaction.closing_date = request.closing_date
    transaction.template_id = template.id

    # Get existing milestone titles for duplicate detection
    existing_stmt = (
        select(Milestone)
        .where(Milestone.transaction_id == transaction_id)
    )
    existing_result = await db.execute(existing_stmt)
    existing_milestones = existing_result.scalars().all()
    existing_titles = {m.title.strip().lower() for m in existing_milestones}

    created_count = 0
    skipped = []

    for item in sorted(template.items, key=lambda x: x.sort_order):
        # Check conditional milestones
        if item.is_conditional and item.condition_field and item.condition_not_value:
            field_value = getattr(transaction, item.condition_field, None)
            if field_value and str(field_value).lower() == item.condition_not_value.lower():
                skipped.append(SkippedMilestone(
                    title=item.title,
                    reason=f"Skipped: {item.condition_field} is {item.condition_not_value}",
                ))
                continue

        # Check for duplicates
        if item.title.strip().lower() in existing_titles:
            skipped.append(SkippedMilestone(
                title=item.title,
                reason="Already exists on this transaction",
            ))
            continue

        # Compute due date
        due_date = None
        status = "pending"
        if item.offset_reference == "contract_date":
            due_date = request.contract_execution_date + timedelta(days=item.day_offset)
        elif item.offset_reference == "closing_date":
            if request.closing_date:
                due_date = request.closing_date + timedelta(days=item.day_offset)
            else:
                # No closing date — create with NULL date and pending_date status
                status = "pending_date"

        milestone = Milestone(
            transaction_id=transaction_id,
            type=item.type,
            title=item.title,
            due_date=due_date,
            status=status,
            responsible_party_role=item.responsible_party_role or "buyer_agent",
            reminder_days_before=item.reminder_days_before,
            sort_order=item.sort_order,
            template_item_id=item.id,
            is_auto_generated=True,
        )
        db.add(milestone)
        created_count += 1

    await db.commit()

    return ApplyTemplateResponse(
        milestones_created=created_count,
        milestones_skipped=len(skipped),
        skipped_reasons=skipped,
    )

import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.action_item import ActionItem
from app.models.milestone import Milestone
from app.schemas.action_item import ActionItemCreate, ActionItemUpdate, ActionItemResponse

logger = logging.getLogger(__name__)


async def list_action_items(
    transaction_id: UUID,
    db: AsyncSession,
    status: Optional[str] = None,
    item_type: Optional[str] = None,
) -> List[ActionItemResponse]:
    """List action items for a transaction with optional filtering."""
    stmt = select(ActionItem).where(ActionItem.transaction_id == transaction_id)

    if status:
        stmt = stmt.where(ActionItem.status == status)
    if item_type:
        stmt = stmt.where(ActionItem.type == item_type)

    stmt = stmt.order_by(ActionItem.due_date.asc().nulls_last())
    result = await db.execute(stmt)
    items = result.scalars().all()
    return [ActionItemResponse.model_validate(i) for i in items]


async def create_action_item(
    transaction_id: UUID,
    item_create: ActionItemCreate,
    db: AsyncSession,
    agent_id: Optional[UUID] = None,
) -> ActionItemResponse:
    """Create a manual action item."""
    item = ActionItem(
        transaction_id=transaction_id,
        type=item_create.type,
        title=item_create.title,
        description=item_create.description,
        priority=item_create.priority,
        due_date=item_create.due_date,
        status="pending",
        agent_id=agent_id,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return ActionItemResponse.model_validate(item)


async def update_action_item(
    item_id: UUID,
    item_update: ActionItemUpdate,
    db: AsyncSession,
) -> ActionItemResponse:
    """Update an action item (complete, snooze, dismiss, or edit)."""
    item = await db.get(ActionItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Action item not found")

    update_data = item_update.model_dump(exclude_unset=True)

    # Handle status transitions
    if "status" in update_data:
        new_status = update_data["status"]
        if new_status == "completed":
            update_data["completed_at"] = datetime.now(timezone.utc)
            # If linked to a milestone, also mark it complete
            if item.milestone_id:
                milestone = await db.get(Milestone, item.milestone_id)
                if milestone and milestone.status != "completed":
                    milestone.status = "completed"
                    milestone.completed_at = datetime.now(timezone.utc)

        elif new_status == "snoozed":
            if "snoozed_until" not in update_data:
                raise HTTPException(
                    status_code=400,
                    detail="snoozed_until is required when snoozing an action item",
                )

    for field, value in update_data.items():
        setattr(item, field, value)

    await db.commit()
    await db.refresh(item)
    return ActionItemResponse.model_validate(item)

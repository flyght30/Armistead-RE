import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.email_draft import EmailDraft
from app.schemas.notification import EmailDraftCreate, EmailDraftUpdate, EmailDraftResponse

logger = logging.getLogger(__name__)


async def list_drafts(
    transaction_id: UUID, db: AsyncSession, status: Optional[str] = None
) -> List[EmailDraftResponse]:
    stmt = select(EmailDraft).where(EmailDraft.transaction_id == transaction_id)
    if status:
        stmt = stmt.where(EmailDraft.status == status)
    stmt = stmt.order_by(EmailDraft.created_at.desc())
    result = await db.execute(stmt)
    drafts = result.scalars().all()
    return [EmailDraftResponse.model_validate(d) for d in drafts]


async def get_draft(draft_id: UUID, db: AsyncSession) -> EmailDraftResponse:
    draft = await db.get(EmailDraft, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Email draft not found")
    return EmailDraftResponse.model_validate(draft)


async def create_draft(
    draft_create: EmailDraftCreate, db: AsyncSession
) -> EmailDraftResponse:
    draft = EmailDraft(**draft_create.model_dump())
    db.add(draft)
    await db.commit()
    await db.refresh(draft)
    return EmailDraftResponse.model_validate(draft)


async def update_draft(
    draft_id: UUID, draft_update: EmailDraftUpdate, db: AsyncSession,
    approver_id: Optional[UUID] = None,
) -> EmailDraftResponse:
    draft = await db.get(EmailDraft, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Email draft not found")

    update_data = draft_update.model_dump(exclude_unset=True)

    if "status" in update_data:
        new_status = update_data["status"]
        if new_status == "approved":
            draft.approved_at = datetime.now(timezone.utc)
            draft.approved_by = approver_id
        elif new_status == "rejected":
            draft.rejected_at = datetime.now(timezone.utc)

    for field, value in update_data.items():
        setattr(draft, field, value)

    await db.commit()
    await db.refresh(draft)
    return EmailDraftResponse.model_validate(draft)


async def delete_draft(draft_id: UUID, db: AsyncSession) -> None:
    draft = await db.get(EmailDraft, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Email draft not found")
    await db.delete(draft)
    await db.commit()


async def send_draft(draft_id: UUID, db: AsyncSession) -> EmailDraftResponse:
    """Send an email draft via the delivery service and mark it as sent."""
    from app.services import email_delivery_service

    draft = await db.get(EmailDraft, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Email draft not found")
    if draft.status == "sent":
        raise HTTPException(status_code=400, detail="Draft already sent")
    if not draft.recipient_email:
        raise HTTPException(status_code=422, detail="Draft is missing recipient_email")
    if not draft.subject:
        raise HTTPException(status_code=422, detail="Draft is missing subject")
    if not draft.body_html:
        raise HTTPException(status_code=422, detail="Draft is missing body_html")

    result = await email_delivery_service.send_email(
        to_email=draft.recipient_email,
        subject=draft.subject,
        html_body=draft.body_html,
    )

    if result.get("status") == "failed":
        raise HTTPException(
            status_code=502,
            detail=f"Email delivery failed: {result.get('error', 'Unknown error')}",
        )

    draft.status = "sent"
    draft.sent_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(draft)
    return EmailDraftResponse.model_validate(draft)

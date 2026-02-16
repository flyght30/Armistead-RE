from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session
from app.auth import get_current_agent_id
from app.schemas.notification import EmailDraftCreate, EmailDraftUpdate, EmailDraftResponse
from app.services import email_draft_service

router = APIRouter()


@router.get("/transactions/{transaction_id}/email-drafts", response_model=List[EmailDraftResponse])
async def list_email_drafts(
    transaction_id: UUID,
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_async_session),
):
    return await email_draft_service.list_drafts(transaction_id, db, status=status)


@router.get("/email-drafts/{draft_id}", response_model=EmailDraftResponse)
async def get_email_draft(
    draft_id: UUID,
    db: AsyncSession = Depends(get_async_session),
):
    return await email_draft_service.get_draft(draft_id, db)


@router.post("/email-drafts", response_model=EmailDraftResponse)
async def create_email_draft(
    draft_create: EmailDraftCreate,
    db: AsyncSession = Depends(get_async_session),
):
    return await email_draft_service.create_draft(draft_create, db)


@router.patch("/email-drafts/{draft_id}", response_model=EmailDraftResponse)
async def update_email_draft(
    draft_id: UUID,
    draft_update: EmailDraftUpdate,
    db: AsyncSession = Depends(get_async_session),
    agent_id: UUID = Depends(get_current_agent_id),
):
    return await email_draft_service.update_draft(draft_id, draft_update, db, approver_id=agent_id)


@router.delete("/email-drafts/{draft_id}")
async def delete_email_draft(
    draft_id: UUID,
    db: AsyncSession = Depends(get_async_session),
):
    await email_draft_service.delete_draft(draft_id, db)
    return {"success": True}


@router.post("/email-drafts/{draft_id}/send", response_model=EmailDraftResponse)
async def send_email_draft(
    draft_id: UUID,
    db: AsyncSession = Depends(get_async_session),
):
    return await email_draft_service.send_draft(draft_id, db)

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session
from app.schemas.portal import (
    PortalAccessCreate, PortalAccessResponse,
    PortalUploadResponse, PortalUploadReview, PortalTransactionView,
)
from app.services import portal_service

router = APIRouter()

DEV_AGENT_ID = "00000000-0000-0000-0000-000000000001"


# --- Agent-facing portal management ---

@router.post("/transactions/{transaction_id}/portal-access", response_model=PortalAccessResponse)
async def create_portal_access(
    transaction_id: UUID,
    access_create: PortalAccessCreate,
    db: AsyncSession = Depends(get_async_session),
):
    return await portal_service.create_portal_access(transaction_id, access_create, db)


@router.get("/transactions/{transaction_id}/portal-access", response_model=List[PortalAccessResponse])
async def list_portal_access(
    transaction_id: UUID,
    db: AsyncSession = Depends(get_async_session),
):
    return await portal_service.list_portal_access(transaction_id, db)


@router.post("/portal-access/{access_id}/revoke")
async def revoke_portal_access(
    access_id: UUID,
    db: AsyncSession = Depends(get_async_session),
):
    await portal_service.revoke_portal_access(access_id, db)
    return {"success": True}


# --- Public portal (token-based) ---

@router.get("/portal/{token}", response_model=PortalTransactionView)
async def get_portal_view(
    token: str,
    db: AsyncSession = Depends(get_async_session),
):
    return await portal_service.get_portal_view(token, db)


# --- Portal uploads (quarantine) ---

@router.get("/transactions/{transaction_id}/portal-uploads", response_model=List[PortalUploadResponse])
async def list_portal_uploads(
    transaction_id: UUID,
    quarantine_status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_async_session),
):
    return await portal_service.list_uploads(transaction_id, db, quarantine_status=quarantine_status)


@router.patch("/portal-uploads/{upload_id}/review", response_model=PortalUploadResponse)
async def review_portal_upload(
    upload_id: UUID,
    review: PortalUploadReview,
    db: AsyncSession = Depends(get_async_session),
):
    reviewer_id = UUID(DEV_AGENT_ID)
    return await portal_service.review_upload(upload_id, review, db, reviewer_id=reviewer_id)

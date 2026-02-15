import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.portal import PortalAccess, PortalAccessLog, PortalUpload
from app.models.transaction import Transaction
from app.models.milestone import Milestone
from app.models.party import Party
from app.schemas.portal import (
    PortalAccessCreate, PortalAccessResponse, PortalAccessLogResponse,
    PortalUploadResponse, PortalUploadReview, PortalTransactionView,
)

logger = logging.getLogger(__name__)


async def create_portal_access(
    transaction_id: UUID, access_create: PortalAccessCreate, db: AsyncSession
) -> PortalAccessResponse:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=access_create.expires_in_days)

    access = PortalAccess(
        transaction_id=transaction_id,
        party_id=access_create.party_id,
        token=token,
        role=access_create.role,
        expires_at=expires_at,
    )
    db.add(access)
    await db.commit()
    await db.refresh(access)
    return PortalAccessResponse.model_validate(access)


async def get_portal_access_by_token(
    token: str, db: AsyncSession
) -> Optional[PortalAccess]:
    stmt = select(PortalAccess).where(
        PortalAccess.token == token,
        PortalAccess.is_revoked == False,
    )
    result = await db.execute(stmt)
    access = result.scalar_one_or_none()
    if not access:
        return None

    # Check expiration
    if access.expires_at < datetime.now(timezone.utc):
        return None

    # Update last access
    access.last_accessed_at = datetime.now(timezone.utc)
    access.access_count += 1
    await db.commit()
    return access


async def revoke_portal_access(access_id: UUID, db: AsyncSession) -> None:
    access = await db.get(PortalAccess, access_id)
    if not access:
        raise HTTPException(status_code=404, detail="Portal access not found")
    access.is_revoked = True
    await db.commit()


async def list_portal_access(
    transaction_id: UUID, db: AsyncSession
) -> List[PortalAccessResponse]:
    stmt = select(PortalAccess).where(
        PortalAccess.transaction_id == transaction_id
    ).order_by(PortalAccess.created_at.desc())
    result = await db.execute(stmt)
    accesses = result.scalars().all()
    return [PortalAccessResponse.model_validate(a) for a in accesses]


async def get_portal_view(
    token: str, db: AsyncSession
) -> PortalTransactionView:
    access = await get_portal_access_by_token(token, db)
    if not access:
        raise HTTPException(status_code=404, detail="Invalid or expired portal link")

    transaction = await db.get(Transaction, access.transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Log access
    log = PortalAccessLog(
        portal_access_id=access.id,
        action="view",
        resource_type="transaction",
    )
    db.add(log)
    await db.commit()

    # Get milestones (filtered for external view)
    ms_stmt = select(Milestone).where(
        Milestone.transaction_id == access.transaction_id
    ).order_by(Milestone.sort_order)
    ms_result = await db.execute(ms_stmt)
    milestones = ms_result.scalars().all()

    # Get parties
    p_stmt = select(Party).where(Party.transaction_id == access.transaction_id)
    p_result = await db.execute(p_stmt)
    parties = p_result.scalars().all()

    # Get party name
    party = await db.get(Party, access.party_id)
    party_name = party.name if party else "Unknown"

    return PortalTransactionView(
        transaction_id=access.transaction_id,
        property_address=transaction.property_address,
        status=transaction.status,
        closing_date=transaction.closing_date,
        milestones=[
            {"id": str(m.id), "title": m.title, "status": m.status,
             "due_date": str(m.due_date) if m.due_date else None}
            for m in milestones
        ],
        parties=[
            {"name": p.name, "role": p.role, "company": p.company}
            for p in parties
        ],
        documents=[],
        role=access.role,
        party_name=party_name,
    )


async def log_portal_action(
    portal_access_id: UUID,
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[UUID] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    db: AsyncSession = None,
) -> None:
    log = PortalAccessLog(
        portal_access_id=portal_access_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(log)
    await db.commit()


# --- Portal Uploads (Quarantine) ---

async def list_uploads(
    transaction_id: UUID, db: AsyncSession,
    quarantine_status: Optional[str] = None,
) -> List[PortalUploadResponse]:
    stmt = select(PortalUpload).where(PortalUpload.transaction_id == transaction_id)
    if quarantine_status:
        stmt = stmt.where(PortalUpload.quarantine_status == quarantine_status)
    stmt = stmt.order_by(PortalUpload.created_at.desc())
    result = await db.execute(stmt)
    uploads = result.scalars().all()
    return [PortalUploadResponse.model_validate(u) for u in uploads]


async def review_upload(
    upload_id: UUID, review: PortalUploadReview, db: AsyncSession,
    reviewer_id: UUID = None,
) -> PortalUploadResponse:
    upload = await db.get(PortalUpload, upload_id)
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")

    upload.quarantine_status = review.quarantine_status
    upload.reviewed_at = datetime.now(timezone.utc)
    upload.reviewed_by = reviewer_id
    if review.rejection_reason:
        upload.rejection_reason = review.rejection_reason

    await db.commit()
    await db.refresh(upload)
    return PortalUploadResponse.model_validate(upload)

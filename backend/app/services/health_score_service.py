import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.transaction import Transaction
from app.models.milestone import Milestone
from app.models.party import Party
from app.models.file import File
from app.schemas.action_item import HealthScoreResponse, HealthScoreBreakdown

logger = logging.getLogger(__name__)


async def compute_health_score(transaction_id: UUID, db: AsyncSession) -> HealthScoreResponse:
    """Compute and cache the health score for a transaction."""
    # Load transaction with relationships
    stmt = (
        select(Transaction)
        .where(Transaction.id == transaction_id)
        .options(
            selectinload(Transaction.milestones),
            selectinload(Transaction.parties),
            selectinload(Transaction.files),
        )
    )
    result = await db.execute(stmt)
    transaction = result.scalar_one_or_none()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    now = datetime.now(timezone.utc)
    score = 100.0

    # --- Factor 1: Overdue milestones (-20 each, capped at score floor of 10) ---
    overdue_milestones = [
        m for m in transaction.milestones
        if m.due_date and m.status not in ("completed", "pending_date")
        and m.due_date < now
    ]
    overdue_count = len(overdue_milestones)
    overdue_penalty = min(overdue_count * 20, 90)  # floor at 10
    score -= overdue_penalty

    # --- Factor 2: Milestones due within 3 days with no action (-10 each) ---
    upcoming_no_action = [
        m for m in transaction.milestones
        if m.due_date and m.status == "pending"
        and now <= m.due_date <= now + timedelta(days=3)
    ]
    upcoming_count = len(upcoming_no_action)
    upcoming_penalty = upcoming_count * 10
    score -= upcoming_penalty

    # --- Factor 3: Missing key parties ---
    party_roles = {p.role.lower() for p in transaction.parties}
    missing_parties_details = []
    missing_parties_penalty = 0

    if transaction.status != "draft":
        if "buyer" not in party_roles and "buyer_agent" not in party_roles:
            missing_parties_details.append("buyer")
            missing_parties_penalty += 15
        if "seller" not in party_roles and "seller_agent" not in party_roles:
            missing_parties_details.append("seller")
            missing_parties_penalty += 15
        # Only check for lender on financed deals
        if transaction.financing_type and transaction.financing_type.lower() != "cash":
            if "lender" not in party_roles:
                missing_parties_details.append("lender")
                missing_parties_penalty += 15

    score -= missing_parties_penalty

    # --- Factor 4: Missing contract document ---
    missing_docs_details = []
    missing_docs_penalty = 0
    has_contract = bool(transaction.contract_document_url) or any(
        f.name and "contract" in f.name.lower() for f in transaction.files
    )
    if not has_contract and transaction.status != "draft":
        missing_docs_details.append("contract")
        missing_docs_penalty += 10
    score -= missing_docs_penalty

    # --- Factor 5: Pace ratio (remaining milestones vs days to close) ---
    pace_penalty = 0
    remaining_milestones = len([
        m for m in transaction.milestones
        if m.status not in ("completed", "pending_date")
    ])
    days_to_close = None
    if transaction.closing_date:
        delta = transaction.closing_date - now
        days_to_close = max(delta.days, 1)  # Avoid division by zero
        if days_to_close > 0 and remaining_milestones > 0:
            ratio = remaining_milestones / days_to_close
            if ratio > 0.5:
                pace_penalty = min(int(ratio * 10), 15)
    score -= pace_penalty

    # Clamp score
    score = max(0.0, min(100.0, score))

    # Determine color
    if score <= 40:
        color = "red"
    elif score <= 70:
        color = "yellow"
    else:
        color = "green"

    # Cache on transaction
    transaction.health_score = score
    await db.commit()

    breakdown = HealthScoreBreakdown(
        overdue_milestones={"count": overdue_count, "penalty": overdue_penalty},
        upcoming_no_action={"count": upcoming_count, "penalty": upcoming_penalty},
        missing_parties={"details": missing_parties_details, "penalty": missing_parties_penalty},
        missing_documents={"details": missing_docs_details, "penalty": missing_docs_penalty},
        pace_ratio={
            "remaining_milestones": remaining_milestones,
            "days_to_close": days_to_close,
            "penalty": pace_penalty,
        },
    )

    return HealthScoreResponse(score=score, color=color, breakdown=breakdown)

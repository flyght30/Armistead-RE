import logging
from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.ai_advisor import AIAdvisorMessage
from app.models.risk_alert import RiskAlert
from app.models.transaction import Transaction
from app.models.milestone import Milestone
from app.models.party import Party
from app.schemas.ai_advisor import (
    AdvisorChatRequest, AdvisorChatResponse, AdvisorConversation,
    RiskAlertResponse, RiskAlertUpdate,
    ClosingReadinessResponse, RiskDashboardResponse,
)
from app.config import Settings

logger = logging.getLogger(__name__)
settings = Settings()


async def chat(
    transaction_id: UUID,
    agent_id: UUID,
    request: AdvisorChatRequest,
    db: AsyncSession,
) -> AdvisorChatResponse:
    """Send a message to the AI advisor and get a response."""
    # Save user message
    user_msg = AIAdvisorMessage(
        transaction_id=transaction_id,
        agent_id=agent_id,
        message_text=request.message,
        message_type="user_query",
    )
    db.add(user_msg)
    await db.flush()

    # Gather transaction context
    context = await _build_context(transaction_id, db)

    # Generate AI response
    ai_response_text = await _call_claude(request.message, context, request.context_type)

    # Save AI response
    ai_msg = AIAdvisorMessage(
        transaction_id=transaction_id,
        agent_id=agent_id,
        message_text=ai_response_text,
        message_type="ai_response",
        context_summary={"context_type": request.context_type or "general"},
    )
    db.add(ai_msg)
    await db.commit()
    await db.refresh(ai_msg)

    return AdvisorChatResponse.model_validate(ai_msg)


async def get_conversation(
    transaction_id: UUID, db: AsyncSession
) -> AdvisorConversation:
    """Get full conversation history for a transaction."""
    stmt = (
        select(AIAdvisorMessage)
        .where(AIAdvisorMessage.transaction_id == transaction_id)
        .order_by(AIAdvisorMessage.created_at.asc())
    )
    result = await db.execute(stmt)
    messages = result.scalars().all()
    return AdvisorConversation(
        messages=[AdvisorChatResponse.model_validate(m) for m in messages],
        transaction_id=transaction_id,
    )


async def get_risk_alerts(
    transaction_id: UUID, db: AsyncSession
) -> List[RiskAlertResponse]:
    stmt = (
        select(RiskAlert)
        .where(RiskAlert.transaction_id == transaction_id)
        .order_by(RiskAlert.created_at.desc())
    )
    result = await db.execute(stmt)
    alerts = result.scalars().all()
    return [RiskAlertResponse.model_validate(a) for a in alerts]


async def update_risk_alert(
    alert_id: UUID, update: RiskAlertUpdate, db: AsyncSession
) -> RiskAlertResponse:
    alert = await db.get(RiskAlert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Risk alert not found")
    from datetime import datetime, timezone
    update_data = update.model_dump(exclude_unset=True)
    if update_data.get("is_acknowledged"):
        alert.acknowledged_at = datetime.now(timezone.utc)
    for field, value in update_data.items():
        setattr(alert, field, value)
    await db.commit()
    await db.refresh(alert)
    return RiskAlertResponse.model_validate(alert)


async def get_closing_readiness(
    transaction_id: UUID, db: AsyncSession
) -> ClosingReadinessResponse:
    """Compute closing readiness score for a transaction."""
    transaction = await db.get(Transaction, transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Get milestones
    ms_stmt = select(Milestone).where(Milestone.transaction_id == transaction_id)
    ms_result = await db.execute(ms_stmt)
    milestones = ms_result.scalars().all()

    # Get parties
    p_stmt = select(Party).where(Party.transaction_id == transaction_id)
    p_result = await db.execute(p_stmt)
    parties = p_result.scalars().all()

    total_ms = len(milestones)
    completed_ms = sum(1 for m in milestones if m.status == "completed")
    overdue_ms = sum(1 for m in milestones if m.status == "overdue")

    # Score calculation
    ms_score = (completed_ms / total_ms * 100) if total_ms > 0 else 0
    party_score = 100 if len(parties) >= 2 else 50  # At least buyer + seller agents
    doc_score = 100 if transaction.contract_document_url else 0

    overall = (ms_score * 0.5) + (party_score * 0.25) + (doc_score * 0.25)

    blockers = []
    if overdue_ms > 0:
        blockers.append({"type": "overdue_milestones", "description": f"{overdue_ms} overdue milestone(s)", "severity": "high"})
    if not transaction.contract_document_url:
        blockers.append({"type": "missing_contract", "description": "No contract document uploaded", "severity": "medium"})
    if not transaction.closing_date:
        blockers.append({"type": "no_closing_date", "description": "Closing date not set", "severity": "high"})

    status = "ready" if overall >= 80 else ("at_risk" if overall >= 50 else "not_ready")

    return ClosingReadinessResponse(
        transaction_id=transaction_id,
        overall_score=round(overall, 1),
        status=status,
        categories={
            "milestones": {"score": round(ms_score, 1), "completed": completed_ms, "total": total_ms},
            "documents": {"score": doc_score, "has_contract": bool(transaction.contract_document_url)},
            "parties": {"score": party_score, "count": len(parties)},
            "financials": {"score": 100 if transaction.purchase_price else 0},
        },
        blockers=blockers,
        recommendations=[b["description"] for b in blockers],
    )


async def _build_context(transaction_id: UUID, db: AsyncSession) -> dict:
    """Build context summary for Claude API call."""
    transaction = await db.get(Transaction, transaction_id)
    if not transaction:
        return {}

    ms_stmt = select(Milestone).where(Milestone.transaction_id == transaction_id)
    ms_result = await db.execute(ms_stmt)
    milestones = ms_result.scalars().all()

    p_stmt = select(Party).where(Party.transaction_id == transaction_id)
    p_result = await db.execute(p_stmt)
    parties = p_result.scalars().all()

    return {
        "property_address": transaction.property_address,
        "status": transaction.status,
        "closing_date": str(transaction.closing_date) if transaction.closing_date else None,
        "purchase_price": transaction.purchase_price,
        "milestones": [
            {"title": m.title, "status": m.status, "due_date": str(m.due_date) if m.due_date else None}
            for m in milestones
        ],
        "parties": [{"name": p.name, "role": p.role} for p in parties],
    }


async def _call_claude(message: str, context: dict, context_type: Optional[str] = None) -> str:
    """Call Claude API for advisor response."""
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.claude_api_key)

        system_prompt = (
            "You are an AI advisor for real estate transaction management. "
            "You help real estate agents navigate their transactions, understand risks, "
            "and ensure smooth closings. Be concise and actionable."
        )

        if context_type == "risk":
            system_prompt += " Focus on identifying and explaining risks."
        elif context_type == "closing_readiness":
            system_prompt += " Focus on closing readiness and what needs to be done."

        context_str = f"\nTransaction context: {context}" if context else ""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": f"{message}{context_str}"}],
        )
        return response.content[0].text
    except Exception as e:
        logger.error(f"Claude API call failed: {e}")
        return f"I'm unable to process your request right now. Error: {str(e)}"

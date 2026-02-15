from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session
from app.schemas.ai_advisor import (
    AdvisorChatRequest, AdvisorChatResponse, AdvisorConversation,
    RiskAlertResponse, RiskAlertUpdate,
    ClosingReadinessResponse, RiskDashboardResponse,
)
from app.services import ai_advisor_service

router = APIRouter()

DEV_AGENT_ID = "00000000-0000-0000-0000-000000000001"


@router.post("/transactions/{transaction_id}/advisor/chat", response_model=AdvisorChatResponse)
async def advisor_chat(
    transaction_id: UUID,
    request: AdvisorChatRequest,
    db: AsyncSession = Depends(get_async_session),
):
    agent_id = UUID(DEV_AGENT_ID)
    return await ai_advisor_service.chat(transaction_id, agent_id, request, db)


@router.get("/transactions/{transaction_id}/advisor/conversation", response_model=AdvisorConversation)
async def get_conversation(
    transaction_id: UUID,
    db: AsyncSession = Depends(get_async_session),
):
    return await ai_advisor_service.get_conversation(transaction_id, db)


@router.get("/transactions/{transaction_id}/risk-alerts", response_model=List[RiskAlertResponse])
async def list_risk_alerts(
    transaction_id: UUID,
    db: AsyncSession = Depends(get_async_session),
):
    return await ai_advisor_service.get_risk_alerts(transaction_id, db)


@router.patch("/risk-alerts/{alert_id}", response_model=RiskAlertResponse)
async def update_risk_alert(
    alert_id: UUID,
    update: RiskAlertUpdate,
    db: AsyncSession = Depends(get_async_session),
):
    return await ai_advisor_service.update_risk_alert(alert_id, update, db)


@router.get("/transactions/{transaction_id}/closing-readiness", response_model=ClosingReadinessResponse)
async def get_closing_readiness(
    transaction_id: UUID,
    db: AsyncSession = Depends(get_async_session),
):
    return await ai_advisor_service.get_closing_readiness(transaction_id, db)

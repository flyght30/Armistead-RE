from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


# --- AI Advisor Schemas ---

class AdvisorChatRequest(BaseModel):
    message: str
    context_type: Optional[str] = None  # general, risk, closing_readiness


class AdvisorChatResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    transaction_id: UUID
    agent_id: UUID
    message_text: str
    message_type: str
    context_summary: Optional[dict] = None
    created_at: datetime


class AdvisorConversation(BaseModel):
    messages: list[AdvisorChatResponse]
    transaction_id: UUID


# --- Risk Alert Schemas ---

class RiskAlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    transaction_id: UUID
    agent_id: UUID
    alert_type: str
    severity: str
    message: str
    suggested_action: Optional[str] = None
    is_acknowledged: bool
    acknowledged_at: Optional[datetime] = None
    dismissed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class RiskAlertUpdate(BaseModel):
    is_acknowledged: Optional[bool] = None
    dismissed_at: Optional[datetime] = None


class ClosingReadinessResponse(BaseModel):
    transaction_id: UUID
    overall_score: float  # 0-100
    status: str  # ready, at_risk, not_ready
    categories: dict  # {milestones, documents, parties, financials}
    blockers: list[dict]  # [{type, description, severity}]
    recommendations: list[str]


class RiskDashboardResponse(BaseModel):
    transaction_id: UUID
    risk_score: float
    alerts: list[RiskAlertResponse]
    risk_factors: list[dict]

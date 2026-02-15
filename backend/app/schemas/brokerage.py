from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


# --- Brokerage Schemas ---

class BrokerageCreate(BaseModel):
    name: str
    license_number: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    settings: Optional[dict] = None


class BrokerageUpdate(BaseModel):
    name: Optional[str] = None
    license_number: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    logo_url: Optional[str] = None
    settings: Optional[dict] = None
    is_active: Optional[bool] = None


class BrokerageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    license_number: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    logo_url: Optional[str] = None
    settings: Optional[dict] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


# --- Team Schemas ---

class TeamCreate(BaseModel):
    name: str
    lead_agent_id: Optional[UUID] = None
    settings: Optional[dict] = None


class TeamUpdate(BaseModel):
    name: Optional[str] = None
    lead_agent_id: Optional[UUID] = None
    settings: Optional[dict] = None


class TeamMemberAdd(BaseModel):
    user_id: UUID
    role: str = "member"


class TeamMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    team_id: UUID
    user_id: UUID
    role: str
    created_at: datetime


class TeamResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    brokerage_id: UUID
    name: str
    lead_agent_id: Optional[UUID] = None
    settings: Optional[dict] = None
    members: list[TeamMemberResponse] = []
    created_at: datetime
    updated_at: datetime


# --- Compliance Schemas ---

class ComplianceRuleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    rule_type: str  # document_required, deadline_check, commission_cap, custom
    conditions: dict
    severity: str = "warning"
    is_active: bool = True


class ComplianceRuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    conditions: Optional[dict] = None
    severity: Optional[str] = None
    is_active: Optional[bool] = None


class ComplianceRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    brokerage_id: UUID
    name: str
    description: Optional[str] = None
    rule_type: str
    conditions: dict
    severity: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ComplianceViolationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    rule_id: UUID
    transaction_id: UUID
    agent_id: UUID
    severity: str
    message: str
    resolved: bool
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[UUID] = None
    created_at: datetime


class ComplianceDashboardResponse(BaseModel):
    total_violations: int
    unresolved_count: int
    by_severity: dict  # {info: N, warning: N, violation: N}
    recent_violations: list[ComplianceViolationResponse]


# --- Performance Schemas ---

class PerformanceSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    agent_id: UUID
    brokerage_id: Optional[UUID] = None
    period_start: datetime
    period_end: datetime
    metrics: dict
    created_at: datetime


class AgentPerformanceSummary(BaseModel):
    agent_id: UUID
    agent_name: str
    transactions_closed: int
    total_volume: float
    total_commission: float
    avg_days_to_close: Optional[float] = None
    active_transactions: int

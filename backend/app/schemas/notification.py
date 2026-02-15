from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


# --- Notification Rule Schemas ---

class NotificationRuleCreate(BaseModel):
    milestone_type: str
    days_before: int = 2
    auto_send: bool = False
    recipient_roles: list[str] = []
    escalation_enabled: bool = True
    escalation_days: list[int] = [1, 3, 7]
    template_id: Optional[UUID] = None
    is_active: bool = True


class NotificationRuleUpdate(BaseModel):
    milestone_type: Optional[str] = None
    days_before: Optional[int] = None
    auto_send: Optional[bool] = None
    recipient_roles: Optional[list[str]] = None
    escalation_enabled: Optional[bool] = None
    escalation_days: Optional[list[int]] = None
    template_id: Optional[UUID] = None
    is_active: Optional[bool] = None


class NotificationRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    agent_id: UUID
    milestone_type: str
    days_before: int
    auto_send: bool
    recipient_roles: list[str]
    escalation_enabled: bool
    escalation_days: list[int]
    template_id: Optional[UUID] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


# --- Email Draft Schemas ---

class EmailDraftCreate(BaseModel):
    transaction_id: UUID
    milestone_id: Optional[UUID] = None
    party_id: Optional[UUID] = None
    notification_rule_id: Optional[UUID] = None
    recipient_email: str
    recipient_name: Optional[str] = None
    recipient_role: Optional[str] = None
    subject: str
    body_html: str
    body_text: Optional[str] = None
    email_type: str
    escalation_level: int = 0


class EmailDraftUpdate(BaseModel):
    subject: Optional[str] = None
    body_html: Optional[str] = None
    body_text: Optional[str] = None
    status: Optional[str] = None  # draft, approved, rejected, sent, expired
    rejected_reason: Optional[str] = None


class EmailDraftResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    transaction_id: UUID
    milestone_id: Optional[UUID] = None
    party_id: Optional[UUID] = None
    notification_rule_id: Optional[UUID] = None
    recipient_email: str
    recipient_name: Optional[str] = None
    recipient_role: Optional[str] = None
    subject: str
    body_html: str
    body_text: Optional[str] = None
    email_type: str
    escalation_level: int
    ai_generated: bool
    ai_model_used: Optional[str] = None
    status: str
    approved_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    rejected_reason: Optional[str] = None
    sent_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


# --- Notification Log Schemas ---

class NotificationLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    transaction_id: UUID
    milestone_id: Optional[UUID] = None
    type: str
    escalation_level: int
    recipient_email: str
    recipient_name: Optional[str] = None
    recipient_role: Optional[str] = None
    subject: Optional[str] = None
    status: str
    scheduled_for: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    bounced_at: Optional[datetime] = None
    bounce_reason: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int
    created_at: datetime


# --- Notification Settings ---

class NotificationSettingsUpdate(BaseModel):
    notification_preferences: Optional[dict] = None  # {quiet_hours, channels, frequency}
    timezone: Optional[str] = None


# --- Webhook ---

class ResendWebhookPayload(BaseModel):
    type: str
    data: dict

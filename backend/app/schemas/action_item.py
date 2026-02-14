from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class ActionItemBase(BaseModel):
    type: str  # milestone_due, milestone_overdue, missing_party, missing_document, closing_approaching, custom
    title: str
    description: Optional[str] = None
    priority: str = "medium"  # critical, high, medium, low
    due_date: Optional[datetime] = None


class ActionItemCreate(BaseModel):
    """For manually created action items."""
    title: str
    description: Optional[str] = None
    priority: str = "medium"
    due_date: Optional[datetime] = None
    type: str = "custom"


class ActionItemUpdate(BaseModel):
    status: Optional[str] = None  # completed, snoozed, dismissed
    snoozed_until: Optional[datetime] = None
    title: Optional[str] = None
    priority: Optional[str] = None


class ActionItemResponse(ActionItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    transaction_id: UUID
    milestone_id: Optional[UUID] = None
    status: str
    snoozed_until: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    agent_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime


class TodayViewResponse(BaseModel):
    """Response for the Today View endpoint with grouped action items."""
    overdue: list[ActionItemResponse] = []
    due_today: list[ActionItemResponse] = []
    coming_up: list[ActionItemResponse] = []
    this_week: list[ActionItemResponse] = []
    summary: dict  # { overdue_count, due_today_count, coming_up_count, this_week_count }


class HealthScoreBreakdown(BaseModel):
    overdue_milestones: dict  # { count, penalty }
    upcoming_no_action: dict  # { count, penalty }
    missing_parties: dict  # { details[], penalty }
    missing_documents: dict  # { details[], penalty }
    pace_ratio: dict  # { remaining_milestones, days_to_close, penalty }


class HealthScoreResponse(BaseModel):
    score: float
    color: str  # red, yellow, green
    breakdown: HealthScoreBreakdown

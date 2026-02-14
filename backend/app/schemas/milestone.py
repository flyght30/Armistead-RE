from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class MilestoneBase(BaseModel):
    type: str  # inspection, appraisal, financing, closing, other
    title: str
    due_date: Optional[datetime] = None  # nullable for pending_date milestones
    status: str = "pending"  # pending, completed, overdue, pending_date
    responsible_party_role: str
    notes: Optional[Dict[str, Any]] = None
    reminder_days_before: Optional[int] = None
    sort_order: int = 0


class MilestoneCreate(MilestoneBase):
    pass


class MilestoneUpdate(BaseModel):
    type: Optional[str] = None
    title: Optional[str] = None
    due_date: Optional[datetime] = None
    status: Optional[str] = None
    responsible_party_role: Optional[str] = None
    notes: Optional[Dict[str, Any]] = None
    completed_at: Optional[datetime] = None
    reminder_days_before: Optional[int] = None
    sort_order: Optional[int] = None


class MilestoneResponse(MilestoneBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    transaction_id: UUID
    completed_at: Optional[datetime] = None
    last_reminder_sent_at: Optional[datetime] = None
    template_item_id: Optional[UUID] = None
    is_auto_generated: bool = False
    created_at: datetime
    updated_at: datetime

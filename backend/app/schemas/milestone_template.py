from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


# --- Template Items ---

class MilestoneTemplateItemBase(BaseModel):
    type: str
    title: str
    day_offset: int
    offset_reference: str = "contract_date"
    responsible_party_role: Optional[str] = None
    reminder_days_before: int = 2
    is_conditional: bool = False
    condition_field: Optional[str] = None
    condition_not_value: Optional[str] = None
    sort_order: int = 0


class MilestoneTemplateItemCreate(MilestoneTemplateItemBase):
    pass


class MilestoneTemplateItemResponse(MilestoneTemplateItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    template_id: UUID
    created_at: datetime
    updated_at: datetime


# --- Templates ---

class MilestoneTemplateBase(BaseModel):
    name: str
    state_code: str
    financing_type: str
    representation_side: str
    description: Optional[str] = None


class MilestoneTemplateCreate(MilestoneTemplateBase):
    items: List[MilestoneTemplateItemCreate] = []


class MilestoneTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class MilestoneTemplateResponse(MilestoneTemplateBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_default: bool = False
    is_active: bool = True
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    items: List[MilestoneTemplateItemResponse] = []


class MilestoneTemplateListResponse(MilestoneTemplateBase):
    """Lightweight response without items for list views."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_default: bool = False
    is_active: bool = True
    item_count: Optional[int] = None
    created_at: datetime
    updated_at: datetime


# --- Template Application ---

class ApplyTemplateRequest(BaseModel):
    template_id: UUID
    contract_execution_date: datetime
    closing_date: Optional[datetime] = None


class SkippedMilestone(BaseModel):
    title: str
    reason: str


class ApplyTemplateResponse(BaseModel):
    milestones_created: int
    milestones_skipped: int
    skipped_reasons: List[SkippedMilestone] = []

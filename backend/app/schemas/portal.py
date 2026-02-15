from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


# --- Portal Access Schemas ---

class PortalAccessCreate(BaseModel):
    party_id: UUID
    role: str
    expires_in_days: int = 30


class PortalAccessResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    transaction_id: UUID
    party_id: UUID
    token: str
    role: str
    expires_at: datetime
    is_revoked: bool
    last_accessed_at: Optional[datetime] = None
    access_count: int
    created_at: datetime


class PortalAccessLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    portal_access_id: UUID
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[UUID] = None
    created_at: datetime


# --- Portal Upload Schemas ---

class PortalUploadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    transaction_id: UUID
    party_id: Optional[UUID] = None
    file_name: str
    file_url: str
    content_type: Optional[str] = None
    file_size: Optional[int] = None
    quarantine_status: str
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: datetime


class PortalUploadReview(BaseModel):
    quarantine_status: str  # approved, rejected
    rejection_reason: Optional[str] = None


# --- Portal View (public-facing response) ---

class PortalTransactionView(BaseModel):
    transaction_id: UUID
    property_address: Optional[str] = None
    status: str
    closing_date: Optional[datetime] = None
    milestones: list[dict]  # filtered milestone list
    parties: list[dict]  # filtered party list
    documents: list[dict]  # available documents
    role: str
    party_name: str


class PortalMilestoneAcknowledge(BaseModel):
    milestone_id: UUID
    acknowledged: bool = True

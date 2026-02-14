from pydantic import BaseModel, ConfigDict
from typing import Any, Dict, List, Optional
from uuid import UUID
from datetime import datetime
from .common import PaginationParams
from .party import PartyResponse
from .milestone import MilestoneResponse
from .amendment import AmendmentResponse
from .file import FileResponse
from .inspection import InspectionAnalysisResponse
from .communication import CommunicationResponse


class TransactionBase(BaseModel):
    agent_id: UUID
    representation_side: str
    financing_type: Optional[str] = None
    property_address: Optional[str] = None
    property_city: Optional[str] = None
    property_state: Optional[str] = None
    property_zip: Optional[str] = None
    purchase_price: Optional[Dict[str, Any]] = None
    earnest_money_amount: Optional[Dict[str, Any]] = None
    closing_date: Optional[datetime] = None
    contract_document_url: Optional[str] = None
    special_stipulations: Optional[Dict[str, Any]] = None
    contract_execution_date: Optional[datetime] = None


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    """All fields optional for partial updates."""
    representation_side: Optional[str] = None
    financing_type: Optional[str] = None
    property_address: Optional[str] = None
    property_city: Optional[str] = None
    property_state: Optional[str] = None
    property_zip: Optional[str] = None
    purchase_price: Optional[Dict[str, Any]] = None
    earnest_money_amount: Optional[Dict[str, Any]] = None
    closing_date: Optional[datetime] = None
    contract_document_url: Optional[str] = None
    special_stipulations: Optional[Dict[str, Any]] = None
    contract_execution_date: Optional[datetime] = None


class TransactionResponse(TransactionBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    ai_extraction_confidence: Optional[Dict[str, Any]] = None
    health_score: Optional[float] = None
    template_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    parties: List[PartyResponse] = []


class TransactionDetailResponse(TransactionBase):
    """Full transaction response with all nested resources for detail view."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    ai_extraction_confidence: Optional[Dict[str, Any]] = None
    health_score: Optional[float] = None
    template_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    parties: List[PartyResponse] = []
    milestones: List[MilestoneResponse] = []
    amendments: List[AmendmentResponse] = []
    files: List[FileResponse] = []
    inspection_analyses: List[InspectionAnalysisResponse] = []
    communications: List[CommunicationResponse] = []


class TransactionList(BaseModel):
    items: List[TransactionResponse]
    pagination: PaginationParams

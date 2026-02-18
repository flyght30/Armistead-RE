from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class InspectionItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    analysis_id: UUID
    description: str
    location: str
    severity: str  # minor, moderate, major, critical
    estimated_cost_low: Dict[str, Any]
    estimated_cost_high: Dict[str, Any]
    risk_assessment: str
    recommendation: str
    repair_status: str  # pending, in_progress, completed
    sort_order: int
    report_reference: Optional[str] = None  # e.g., "Page 6, Item 3"
    created_at: datetime
    updated_at: datetime


class InspectionAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    transaction_id: UUID
    report_document_url: str
    executive_summary: str
    total_estimated_cost_low: Dict[str, Any]
    total_estimated_cost_high: Dict[str, Any]
    overall_risk_level: str  # low, medium, high, critical
    items: List[InspectionItemResponse] = []
    created_at: datetime
    updated_at: datetime

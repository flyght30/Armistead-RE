from sqlalchemy import Column, UUID, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSON
from .base_model import BaseModel
from .transaction import Transaction

class InspectionAnalysis(BaseModel):
    __tablename__ = "inspection_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False)
    report_document_url = Column(String, nullable=False)
    executive_summary = Column(String, nullable=False)
    total_estimated_cost_low = Column(JSON, nullable=False)
    total_estimated_cost_high = Column(JSON, nullable=False)
    overall_risk_level = Column(String, nullable=False)

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())

class InspectionItem(BaseModel):
    __tablename__ = "inspection_items"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    analysis_id = Column(UUID(as_uuid=True), ForeignKey("inspection_analyses.id"), nullable=False)
    description = Column(String, nullable=False)
    location = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    estimated_cost_low = Column(JSON, nullable=False)
    estimated_cost_high = Column(JSON, nullable=False)
    risk_assessment = Column(String, nullable=False)
    recommendation = Column(String, nullable=False)
    repair_status = Column(String, nullable=False)
    sort_order = Column(Integer, nullable=False)

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())

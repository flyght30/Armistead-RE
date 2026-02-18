from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from .base_model import BaseModel


class InspectionAnalysis(BaseModel):
    __tablename__ = "inspection_analyses"

    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False)
    report_document_url = Column(String, nullable=False)
    executive_summary = Column(String, nullable=False)
    total_estimated_cost_low = Column(JSON, nullable=False)
    total_estimated_cost_high = Column(JSON, nullable=False)
    overall_risk_level = Column(String, nullable=False)

    # Relationships
    transaction = relationship("Transaction", back_populates="inspection_analyses")
    items = relationship("InspectionItem", back_populates="analysis", cascade="all, delete-orphan")


class InspectionItem(BaseModel):
    __tablename__ = "inspection_items"

    analysis_id = Column(UUID(as_uuid=True), ForeignKey("inspection_analyses.id"), nullable=False)
    description = Column(String, nullable=False)
    location = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    estimated_cost_low = Column(JSON, nullable=False)
    estimated_cost_high = Column(JSON, nullable=False)
    risk_assessment = Column(String, nullable=False)
    recommendation = Column(String, nullable=False)
    repair_status = Column(String, nullable=False, default="pending")
    sort_order = Column(Integer, nullable=False)
    report_reference = Column(String, nullable=True)  # e.g., "Page 6, Item 3"

    # Relationships
    analysis = relationship("InspectionAnalysis", back_populates="items")

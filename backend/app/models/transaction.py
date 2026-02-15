from sqlalchemy import Column, String, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSON, TIMESTAMP
from sqlalchemy.orm import relationship
from .base_model import BaseModel


class Transaction(BaseModel):
    __tablename__ = "transactions"

    agent_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status = Column(String, nullable=False, default="draft")
    representation_side = Column(String, nullable=False)
    financing_type = Column(String, nullable=True)
    property_address = Column(String, nullable=True)
    property_city = Column(String, nullable=True)
    property_state = Column(String, nullable=True)
    property_zip = Column(String, nullable=True)
    purchase_price = Column(JSON, nullable=True)
    earnest_money_amount = Column(JSON, nullable=True)
    closing_date = Column(TIMESTAMP(timezone=True), nullable=True)
    contract_document_url = Column(String, nullable=True)
    special_stipulations = Column(JSON, nullable=True)
    ai_extraction_confidence = Column(JSON, nullable=True)

    # Phase 1: New fields
    contract_execution_date = Column(TIMESTAMP(timezone=True), nullable=True)
    health_score = Column(Float, nullable=True)
    template_id = Column(UUID(as_uuid=True), ForeignKey("milestone_templates.id", ondelete="SET NULL"), nullable=True)

    # Phase 2: Notification overrides
    notification_overrides = Column(JSON, nullable=True)  # per-transaction notification settings

    # Relationships
    agent = relationship("User", back_populates="transactions", foreign_keys=[agent_id])
    parties = relationship("Party", back_populates="transaction", cascade="all, delete-orphan")
    milestones = relationship("Milestone", back_populates="transaction", cascade="all, delete-orphan")
    communications = relationship("Communication", back_populates="transaction", cascade="all, delete-orphan")
    amendments = relationship("Amendment", back_populates="transaction", cascade="all, delete-orphan")
    inspection_analyses = relationship("InspectionAnalysis", back_populates="transaction", cascade="all, delete-orphan")
    files = relationship("File", back_populates="transaction")
    action_items = relationship("ActionItem", back_populates="transaction", cascade="all, delete-orphan")
    template = relationship("MilestoneTemplate", back_populates="transactions", foreign_keys=[template_id])
    commissions = relationship("TransactionCommission", back_populates="transaction", cascade="all, delete-orphan")
    risk_alerts = relationship("RiskAlert", back_populates="transaction", cascade="all, delete-orphan")
    ai_messages = relationship("AIAdvisorMessage", back_populates="transaction", cascade="all, delete-orphan")
    email_drafts = relationship("EmailDraft", back_populates="transaction", cascade="all, delete-orphan")
    notification_logs = relationship("NotificationLog", back_populates="transaction", cascade="all, delete-orphan")

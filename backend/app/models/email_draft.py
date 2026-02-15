from sqlalchemy import Column, String, Boolean, Text, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.orm import relationship
from .base_model import BaseModel


class EmailDraft(BaseModel):
    __tablename__ = "email_drafts"

    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False)
    milestone_id = Column(UUID(as_uuid=True), ForeignKey("milestones.id", ondelete="SET NULL"), nullable=True)
    party_id = Column(UUID(as_uuid=True), ForeignKey("parties.id", ondelete="SET NULL"), nullable=True)
    notification_rule_id = Column(UUID(as_uuid=True), ForeignKey("notification_rules.id", ondelete="SET NULL"), nullable=True)
    recipient_email = Column(String(200), nullable=False)
    recipient_name = Column(String(200), nullable=True)
    recipient_role = Column(String(30), nullable=True)
    subject = Column(String(500), nullable=False)
    body_html = Column(Text, nullable=False)
    body_text = Column(Text, nullable=True)
    email_type = Column(String(50), nullable=False)
    escalation_level = Column(Integer, nullable=False, default=0)
    ai_generated = Column(Boolean, nullable=False, default=False)
    ai_model_used = Column(String(50), nullable=True)
    original_ai_content = Column(Text, nullable=True)
    status = Column(String(30), nullable=False, default="draft")
    approved_at = Column(TIMESTAMP(timezone=True), nullable=True)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    rejected_at = Column(TIMESTAMP(timezone=True), nullable=True)
    rejected_reason = Column(Text, nullable=True)
    sent_at = Column(TIMESTAMP(timezone=True), nullable=True)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=True)

    # Relationships
    transaction = relationship("Transaction", back_populates="email_drafts", foreign_keys=[transaction_id])
    milestone = relationship("Milestone", foreign_keys=[milestone_id])
    party = relationship("Party", foreign_keys=[party_id])
    rule = relationship("NotificationRule", foreign_keys=[notification_rule_id])
    approver = relationship("User", foreign_keys=[approved_by])

from sqlalchemy import Column, String, Integer, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.orm import relationship
from .base_model import BaseModel


class NotificationLog(BaseModel):
    __tablename__ = "notification_log"

    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False)
    milestone_id = Column(UUID(as_uuid=True), ForeignKey("milestones.id", ondelete="SET NULL"), nullable=True)
    communication_id = Column(UUID(as_uuid=True), ForeignKey("communications.id", ondelete="SET NULL"), nullable=True)
    rule_id = Column(UUID(as_uuid=True), ForeignKey("notification_rules.id", ondelete="SET NULL"), nullable=True)
    draft_id = Column(UUID(as_uuid=True), ForeignKey("email_drafts.id", ondelete="SET NULL"), nullable=True)
    type = Column(String(50), nullable=False)
    escalation_level = Column(Integer, nullable=False, default=0)
    recipient_email = Column(String(200), nullable=False)
    recipient_name = Column(String(200), nullable=True)
    recipient_role = Column(String(30), nullable=True)
    subject = Column(String(500), nullable=True)
    status = Column(String(30), nullable=False, default="pending")
    resend_message_id = Column(String(200), nullable=True)
    scheduled_for = Column(TIMESTAMP(timezone=True), nullable=True)
    sent_at = Column(TIMESTAMP(timezone=True), nullable=True)
    delivered_at = Column(TIMESTAMP(timezone=True), nullable=True)
    opened_at = Column(TIMESTAMP(timezone=True), nullable=True)
    clicked_at = Column(TIMESTAMP(timezone=True), nullable=True)
    bounced_at = Column(TIMESTAMP(timezone=True), nullable=True)
    bounce_reason = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    idempotency_key = Column(String(200), unique=True, nullable=True)

    # Relationships
    transaction = relationship("Transaction", back_populates="notification_logs", foreign_keys=[transaction_id])
    milestone = relationship("Milestone", foreign_keys=[milestone_id])
    communication = relationship("Communication", foreign_keys=[communication_id])
    rule = relationship("NotificationRule", foreign_keys=[rule_id])

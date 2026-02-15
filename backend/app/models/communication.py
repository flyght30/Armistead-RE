from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSON, TIMESTAMP
from sqlalchemy.orm import relationship
from .base_model import BaseModel


class Communication(BaseModel):
    __tablename__ = "communications"

    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False)
    milestone_id = Column(UUID(as_uuid=True), ForeignKey("milestones.id"), nullable=True)
    recipient_party_id = Column(UUID(as_uuid=True), ForeignKey("parties.id"), nullable=True)
    type = Column(String, nullable=False)
    recipient_email = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    body = Column(String, nullable=False)
    attachments = Column(JSON, nullable=True)
    status = Column(String, nullable=False)
    resend_message_id = Column(UUID(as_uuid=True), nullable=True)
    sent_at = Column(TIMESTAMP(timezone=True), nullable=True)
    opened_at = Column(TIMESTAMP(timezone=True), nullable=True)
    clicked_at = Column(TIMESTAMP(timezone=True), nullable=True)
    template_used = Column(String, nullable=True)

    # Phase 2: Delivery tracking
    delivery_status = Column(String(30), nullable=True)  # delivered, bounced, complained
    bounce_reason = Column(String, nullable=True)
    notification_log_id = Column(UUID(as_uuid=True), nullable=True)

    # Relationships
    transaction = relationship("Transaction", back_populates="communications")
    milestone = relationship("Milestone", back_populates="communications")
    recipient_party = relationship("Party", back_populates="communications")

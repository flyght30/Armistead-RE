from sqlalchemy import Column, String, Boolean, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSON, TIMESTAMP
from sqlalchemy.orm import relationship
from .base_model import BaseModel


class Party(BaseModel):
    __tablename__ = "parties"

    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False)
    role = Column(String, nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    company = Column(String, nullable=True)
    is_primary = Column(Boolean, default=False)
    notes = Column(JSON, nullable=True)

    # Phase 2: Notification fields
    notification_preference = Column(String(20), nullable=True, default="email")
    notification_cooldown_hours = Column(Integer, nullable=True, default=24)
    last_notification_sent_at = Column(TIMESTAMP(timezone=True), nullable=True)
    email_bounced = Column(Boolean, default=False)
    bounced_at = Column(TIMESTAMP(timezone=True), nullable=True)
    unsubscribed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    unsubscribe_token = Column(String, unique=True, nullable=True)

    # Relationships
    transaction = relationship("Transaction", back_populates="parties")
    communications = relationship("Communication", back_populates="recipient_party")

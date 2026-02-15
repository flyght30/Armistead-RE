from sqlalchemy import Column, String, Boolean, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.orm import relationship
from .base_model import BaseModel


class RiskAlert(BaseModel):
    __tablename__ = "risk_alerts"

    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    alert_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)  # low, medium, high, critical
    message = Column(Text, nullable=False)
    suggested_action = Column(Text, nullable=True)
    is_acknowledged = Column(Boolean, default=False)
    acknowledged_at = Column(TIMESTAMP(timezone=True), nullable=True)
    dismissed_at = Column(TIMESTAMP(timezone=True), nullable=True)

    # Relationships
    transaction = relationship("Transaction", back_populates="risk_alerts", foreign_keys=[transaction_id])
    agent = relationship("User", foreign_keys=[agent_id])

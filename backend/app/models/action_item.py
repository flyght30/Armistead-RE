from sqlalchemy import Column, String, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.orm import relationship
from .base_model import BaseModel


class ActionItem(BaseModel):
    """Action items shown in the Today View — auto-generated or manual."""
    __tablename__ = "action_items"

    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False)
    milestone_id = Column(UUID(as_uuid=True), ForeignKey("milestones.id", ondelete="SET NULL"), nullable=True)
    type = Column(String(50), nullable=False)  # milestone_due, milestone_overdue, missing_party, missing_document, closing_approaching, custom
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(String(20), nullable=False, default="medium")  # critical, high, medium, low
    status = Column(String(20), nullable=False, default="pending")  # pending, snoozed, completed, dismissed
    due_date = Column(TIMESTAMP(timezone=True), nullable=True)
    snoozed_until = Column(TIMESTAMP(timezone=True), nullable=True)
    completed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Relationships
    transaction = relationship("Transaction", back_populates="action_items")
    milestone = relationship("Milestone", back_populates="action_items")
    agent = relationship("User", foreign_keys=[agent_id])

from sqlalchemy import Column, String, Integer, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSON, TIMESTAMP
from sqlalchemy.orm import relationship
from .base_model import BaseModel


class Milestone(BaseModel):
    __tablename__ = "milestones"

    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False)
    type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    due_date = Column(TIMESTAMP(timezone=True), nullable=True)  # nullable for pending_date milestones
    status = Column(String, nullable=False)
    responsible_party_role = Column(String, nullable=False)
    notes = Column(JSON, nullable=True)
    completed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    reminder_days_before = Column(Integer, nullable=True)
    last_reminder_sent_at = Column(TIMESTAMP(timezone=True), nullable=True)
    sort_order = Column(Integer, nullable=False)

    # Phase 2: Nudge engine fields
    reminder_sent_count = Column(Integer, nullable=False, default=0)
    escalation_level = Column(Integer, nullable=False, default=0)
    reminders_paused_until = Column(TIMESTAMP(timezone=True), nullable=True)

    # Phase 1: New fields
    template_item_id = Column(UUID(as_uuid=True), ForeignKey("milestone_template_items.id", ondelete="SET NULL"), nullable=True)
    is_auto_generated = Column(Boolean, default=False)

    # Relationships
    transaction = relationship("Transaction", back_populates="milestones")
    communications = relationship("Communication", back_populates="milestone")
    action_items = relationship("ActionItem", back_populates="milestone")

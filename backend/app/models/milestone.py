from sqlalchemy import Column, UUID, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSON
from .base_model import BaseModel
from .transaction import Transaction

class Milestone(BaseModel):
    __tablename__ = "milestones"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False)
    type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    due_date = Column(TIMESTAMP(timezone=True), nullable=False)
    status = Column(String, nullable=False)
    responsible_party_role = Column(String, nullable=False)
    notes = Column(JSON, nullable=True)
    completed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    reminder_days_before = Column(Integer, nullable=True)
    last_reminder_sent_at = Column(TIMESTAMP(timezone=True), nullable=True)
    sort_order = Column(Integer, nullable=False)

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())

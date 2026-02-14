from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from .base_model import BaseModel


class Amendment(BaseModel):
    __tablename__ = "amendments"

    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False)
    field_changed = Column(String, nullable=False)
    old_value = Column(JSON, nullable=False)
    new_value = Column(JSON, nullable=False)
    reason = Column(String, nullable=False)
    changed_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    notification_sent = Column(Boolean, default=False)

    # Relationships
    transaction = relationship("Transaction", back_populates="amendments")
    changed_by = relationship("User", back_populates="amendments")

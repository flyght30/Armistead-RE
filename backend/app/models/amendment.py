from sqlalchemy import Column, UUID, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSON
from .base_model import BaseModel
from .transaction import Transaction
from .user import User

class Amendment(BaseModel):
    __tablename__ = "amendments"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False)
    field_changed = Column(String, nullable=False)
    old_value = Column(JSON, nullable=False)
    new_value = Column(JSON, nullable=False)
    reason = Column(String, nullable=False)
    changed_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    notification_sent = Column(Boolean, default=False)

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())

from sqlalchemy import Column, UUID, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSON
from .base_model import BaseModel
from .transaction import Transaction

class Party(BaseModel):
    __tablename__ = "parties"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False)
    role = Column(String, nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    company = Column(String, nullable=True)
    is_primary = Column(Boolean, default=False)
    notes = Column(JSON, nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())

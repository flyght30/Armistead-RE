from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from .base_model import BaseModel


class Party(BaseModel):
    __tablename__ = "parties"

    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False)
    role = Column(String, nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    company = Column(String, nullable=True)
    is_primary = Column(Boolean, default=False)
    notes = Column(JSON, nullable=True)

    # Relationships
    transaction = relationship("Transaction", back_populates="parties")
    communications = relationship("Communication", back_populates="recipient_party")

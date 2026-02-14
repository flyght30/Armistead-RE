from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship
from .base_model import BaseModel


class User(BaseModel):
    __tablename__ = "users"

    clerk_id = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    brokerage_name = Column(String, nullable=True)
    license_number = Column(String, nullable=True)
    state = Column(String, nullable=True)
    email_signature = Column(JSON, nullable=True)
    settings = Column(JSON, nullable=True)

    # Relationships
    transactions = relationship("Transaction", back_populates="agent", foreign_keys="Transaction.agent_id")
    amendments = relationship("Amendment", back_populates="changed_by")
    email_templates = relationship("EmailTemplate", back_populates="agent")

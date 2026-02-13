from sqlalchemy import Column, UUID, String, JSON
from sqlalchemy.dialects.postgresql import TIMESTAMP
from .base_model import BaseModel

class User(BaseModel):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    clerk_id = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    brokerage_name = Column(String, nullable=True)
    license_number = Column(String, nullable=True)
    state = Column(String, nullable=True)
    email_signature = Column(JSON, nullable=True)
    settings = Column(JSON, nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())

from sqlalchemy import Column, UUID, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSON
from .base_model import BaseModel
from .user import User

class EmailTemplate(BaseModel):
    __tablename__ = "email_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    representation_side = Column(String, nullable=True)
    recipient_role = Column(String, nullable=False)
    subject_template = Column(String, nullable=False)
    body_template = Column(String, nullable=False)
    is_active = Column(Boolean, default=False)

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())

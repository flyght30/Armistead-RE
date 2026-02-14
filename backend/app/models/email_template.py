from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base_model import BaseModel


class EmailTemplate(BaseModel):
    __tablename__ = "email_templates"

    agent_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    representation_side = Column(String, nullable=True)
    recipient_role = Column(String, nullable=False)
    subject_template = Column(String, nullable=False)
    body_template = Column(String, nullable=False)
    is_active = Column(Boolean, default=False)

    # Relationships
    agent = relationship("User", back_populates="email_templates")

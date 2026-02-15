from sqlalchemy import Column, String, Integer, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from .base_model import BaseModel


class NotificationRule(BaseModel):
    __tablename__ = "notification_rules"

    agent_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    milestone_type = Column(String(50), nullable=False)  # specific type or '*' for all
    days_before = Column(Integer, nullable=False, default=2)
    auto_send = Column(Boolean, nullable=False, default=False)
    recipient_roles = Column(ARRAY(String), nullable=False, default=[])
    escalation_enabled = Column(Boolean, nullable=False, default=True)
    escalation_days = Column(ARRAY(Integer), nullable=False, default=[1, 3, 7])
    template_id = Column(UUID(as_uuid=True), ForeignKey("email_templates.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    # Relationships
    agent = relationship("User", foreign_keys=[agent_id])
    template = relationship("EmailTemplate", foreign_keys=[template_id])

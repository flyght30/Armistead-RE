from sqlalchemy import Column, UUID, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSON
from .base_model import BaseModel
from .transaction import Transaction
from .party import Party
from .milestone import Milestone

class Communication(BaseModel):
    __tablename__ = "communications"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False)
    milestone_id = Column(UUID(as_uuid=True), ForeignKey("milestones.id"), nullable=True)
    recipient_party_id = Column(UUID(as_uuid=True), ForeignKey("parties.id"), nullable=True)
    type = Column(String, nullable=False)
    recipient_email = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    body = Column(String, nullable=False)
    attachments = Column(JSON, nullable=True)
    status = Column(String, nullable=False)
    resend_message_id = Column(UUID(as_uuid=True), nullable=True)
    sent_at = Column(TIMESTAMP(timezone=True), nullable=False)
    opened_at = Column(TIMESTAMP(timezone=True), nullable=True)
    clicked_at = Column(TIMESTAMP(timezone=True), nullable=True)
    template_used = Column(String, nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())

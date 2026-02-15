from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from .base_model import BaseModel


class AIAdvisorMessage(BaseModel):
    __tablename__ = "ai_advisor_messages"

    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    message_text = Column(Text, nullable=False)
    message_type = Column(String(20), nullable=False)  # user_query, ai_response
    context_summary = Column(JSON, nullable=True)

    # Relationships
    transaction = relationship("Transaction", back_populates="ai_messages", foreign_keys=[transaction_id])
    agent = relationship("User", foreign_keys=[agent_id])

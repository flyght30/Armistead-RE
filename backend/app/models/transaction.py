from sqlalchemy import Column, UUID, ForeignKey, String, JSON
from sqlalchemy.dialects.postgresql import TIMESTAMP
from .base_model import BaseModel
from .user import User

class Transaction(BaseModel):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status = Column(String, nullable=False)
    representation_side = Column(String, nullable=False)
    financing_type = Column(String, nullable=True)
    property_address = Column(String, nullable=True)
    property_city = Column(String, nullable=True)
    property_state = Column(String, nullable=True)
    property_zip = Column(String, nullable=True)
    purchase_price = Column(JSON, nullable=True)
    earnest_money_amount = Column(JSON, nullable=True)
    closing_date = Column(TIMESTAMP(timezone=True), nullable=True)
    contract_document_url = Column(String, nullable=True)
    special_stipulations = Column(JSON, nullable=True)
    ai_extraction_confidence = Column(JSON, nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())

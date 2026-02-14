from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base_model import BaseModel


class File(BaseModel):
    __tablename__ = "files"

    name = Column(String, nullable=False)
    content_type = Column(String, nullable=False)
    url = Column(String, nullable=False)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=True)

    # Relationships
    transaction = relationship("Transaction", back_populates="files")

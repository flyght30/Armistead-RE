from sqlalchemy import Column, String, Boolean, Integer, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSON, TIMESTAMP
from sqlalchemy.orm import relationship
from .base_model import BaseModel


class PortalAccess(BaseModel):
    __tablename__ = "portal_access"

    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False)
    party_id = Column(UUID(as_uuid=True), ForeignKey("parties.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(200), unique=True, nullable=False, index=True)
    role = Column(String(30), nullable=False)  # buyer, seller, lender, title_company, etc.
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    is_revoked = Column(Boolean, default=False)
    last_accessed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    access_count = Column(Integer, default=0)

    # Relationships
    transaction = relationship("Transaction", foreign_keys=[transaction_id])
    party = relationship("Party", foreign_keys=[party_id])
    access_logs = relationship("PortalAccessLog", back_populates="portal_access", cascade="all, delete-orphan")


class PortalAccessLog(BaseModel):
    __tablename__ = "portal_access_logs"

    portal_access_id = Column(UUID(as_uuid=True), ForeignKey("portal_access.id", ondelete="CASCADE"), nullable=False)
    action = Column(String(50), nullable=False)  # view, download, upload, acknowledge
    resource_type = Column(String(50), nullable=True)  # milestone, document, timeline
    resource_id = Column(UUID(as_uuid=True), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)

    # Relationships
    portal_access = relationship("PortalAccess", back_populates="access_logs")


class PortalUpload(BaseModel):
    __tablename__ = "portal_uploads"

    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False)
    portal_access_id = Column(UUID(as_uuid=True), ForeignKey("portal_access.id", ondelete="SET NULL"), nullable=True)
    party_id = Column(UUID(as_uuid=True), ForeignKey("parties.id", ondelete="SET NULL"), nullable=True)
    file_name = Column(String(255), nullable=False)
    file_url = Column(String, nullable=False)
    content_type = Column(String(100), nullable=True)
    file_size = Column(Integer, nullable=True)
    quarantine_status = Column(String(30), nullable=False, default="pending")  # pending, approved, rejected
    reviewed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # Relationships
    transaction = relationship("Transaction", foreign_keys=[transaction_id])
    portal_access = relationship("PortalAccess", foreign_keys=[portal_access_id])
    party = relationship("Party", foreign_keys=[party_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by])

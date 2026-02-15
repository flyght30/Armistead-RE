from sqlalchemy import Column, String, Boolean, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from .base_model import BaseModel


class CommissionConfig(BaseModel):
    __tablename__ = "commission_configs"

    agent_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False)
    commission_type = Column(String(20), nullable=False, default="percentage")
    default_rate = Column(Numeric(5, 4), nullable=True)
    default_flat_amount = Column(Numeric(12, 2), nullable=True)
    tiered_rates = Column(JSON, nullable=True)
    broker_split_percentage = Column(Numeric(5, 4), nullable=True)
    default_referral_fee_percentage = Column(Numeric(5, 4), nullable=True)
    team_splits = Column(JSON, nullable=True)

    # Relationships
    agent = relationship("User", foreign_keys=[agent_id])


class TransactionCommission(BaseModel):
    __tablename__ = "transaction_commissions"

    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), unique=True, nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    commission_type = Column(String(20), nullable=False, default="percentage")
    rate = Column(Numeric(5, 4), nullable=True)
    flat_amount = Column(Numeric(12, 2), nullable=True)
    tiered_rates = Column(JSON, nullable=True)
    gross_commission = Column(Numeric(12, 2), nullable=True)
    is_manual_override = Column(Boolean, default=False)
    projected_net = Column(Numeric(12, 2), nullable=True)
    actual_net = Column(Numeric(12, 2), nullable=True)
    actual_gross = Column(Numeric(12, 2), nullable=True)
    status = Column(String(20), nullable=False, default="projected")
    is_dual_agency = Column(Boolean, default=False)
    notes = Column(String, nullable=True)

    # Relationships
    transaction = relationship("Transaction", back_populates="commissions", foreign_keys=[transaction_id])
    agent = relationship("User", foreign_keys=[agent_id])
    splits = relationship("CommissionSplit", back_populates="commission", cascade="all, delete-orphan")


class CommissionSplit(BaseModel):
    __tablename__ = "commission_splits"

    transaction_commission_id = Column(UUID(as_uuid=True), ForeignKey("transaction_commissions.id", ondelete="CASCADE"), nullable=False)
    split_type = Column(String(20), nullable=False)
    recipient_name = Column(String, nullable=False)
    is_percentage = Column(Boolean, default=True)
    percentage = Column(Numeric(5, 4), nullable=True)
    flat_amount = Column(Numeric(12, 2), nullable=True)
    calculated_amount = Column(Numeric(12, 2), nullable=True)

    # Relationships
    commission = relationship("TransactionCommission", back_populates="splits")

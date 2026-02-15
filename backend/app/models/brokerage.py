from sqlalchemy import Column, String, Boolean, Integer, Text, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSON, TIMESTAMP
from sqlalchemy.orm import relationship
from .base_model import BaseModel


class Brokerage(BaseModel):
    __tablename__ = "brokerages"

    name = Column(String(200), nullable=False)
    license_number = Column(String(100), nullable=True)
    address = Column(String, nullable=True)
    phone = Column(String(30), nullable=True)
    email = Column(String(200), nullable=True)
    logo_url = Column(String, nullable=True)
    settings = Column(JSON, nullable=True)  # brokerage-wide settings
    is_active = Column(Boolean, default=True)

    # Relationships
    teams = relationship("Team", back_populates="brokerage", cascade="all, delete-orphan")
    compliance_rules = relationship("ComplianceRule", back_populates="brokerage", cascade="all, delete-orphan")


class Team(BaseModel):
    __tablename__ = "teams"

    brokerage_id = Column(UUID(as_uuid=True), ForeignKey("brokerages.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=False)
    lead_agent_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    settings = Column(JSON, nullable=True)

    # Relationships
    brokerage = relationship("Brokerage", back_populates="teams")
    lead_agent = relationship("User", foreign_keys=[lead_agent_id])
    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")


class TeamMember(BaseModel):
    __tablename__ = "team_members"

    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(30), nullable=False, default="member")  # member, lead, admin

    # Relationships
    team = relationship("Team", back_populates="members")
    user = relationship("User", foreign_keys=[user_id])


class ComplianceRule(BaseModel):
    __tablename__ = "compliance_rules"

    brokerage_id = Column(UUID(as_uuid=True), ForeignKey("brokerages.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    rule_type = Column(String(50), nullable=False)  # document_required, deadline_check, commission_cap, custom
    conditions = Column(JSON, nullable=False)  # rule logic as JSON
    severity = Column(String(20), nullable=False, default="warning")  # info, warning, violation
    is_active = Column(Boolean, default=True)

    # Relationships
    brokerage = relationship("Brokerage", back_populates="compliance_rules")
    violations = relationship("ComplianceViolation", back_populates="rule", cascade="all, delete-orphan")


class ComplianceViolation(BaseModel):
    __tablename__ = "compliance_violations"

    rule_id = Column(UUID(as_uuid=True), ForeignKey("compliance_rules.id", ondelete="CASCADE"), nullable=False)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    severity = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    resolved = Column(Boolean, default=False)
    resolved_at = Column(TIMESTAMP(timezone=True), nullable=True)
    resolved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Relationships
    rule = relationship("ComplianceRule", back_populates="violations")
    transaction = relationship("Transaction", foreign_keys=[transaction_id])
    agent = relationship("User", foreign_keys=[agent_id])
    resolver = relationship("User", foreign_keys=[resolved_by])


class PerformanceSnapshot(BaseModel):
    __tablename__ = "performance_snapshots"

    agent_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    brokerage_id = Column(UUID(as_uuid=True), ForeignKey("brokerages.id"), nullable=True)
    period_start = Column(TIMESTAMP(timezone=True), nullable=False)
    period_end = Column(TIMESTAMP(timezone=True), nullable=False)
    metrics = Column(JSON, nullable=False)  # { transactions_closed, volume, avg_days_to_close, commission_total, ... }

    # Relationships
    agent = relationship("User", foreign_keys=[agent_id])
    brokerage = relationship("Brokerage", foreign_keys=[brokerage_id])

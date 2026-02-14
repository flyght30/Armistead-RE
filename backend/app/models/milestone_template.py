from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.orm import relationship
from .base_model import BaseModel


class MilestoneTemplate(BaseModel):
    """Defines a reusable set of milestones for a state/financing/side combo."""
    __tablename__ = "milestone_templates"

    name = Column(String(200), nullable=False)
    state_code = Column(String(2), nullable=False)
    financing_type = Column(String(30), nullable=False)  # conventional, fha, va, cash
    representation_side = Column(String(10), nullable=False)  # buyer, seller
    description = Column(Text, nullable=True)
    is_default = Column(Boolean, default=False)  # system-provided template
    is_active = Column(Boolean, default=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # NULL for system templates

    # Relationships
    items = relationship(
        "MilestoneTemplateItem",
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="MilestoneTemplateItem.sort_order",
    )
    creator = relationship("User", foreign_keys=[created_by])
    transactions = relationship("Transaction", back_populates="template")


class MilestoneTemplateItem(BaseModel):
    """A single milestone definition within a template."""
    __tablename__ = "milestone_template_items"

    template_id = Column(UUID(as_uuid=True), ForeignKey("milestone_templates.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(50), nullable=False)  # inspection, appraisal, financing, title, closing, etc.
    title = Column(String(200), nullable=False)
    day_offset = Column(Integer, nullable=False)  # positive = from contract, negative = from closing
    offset_reference = Column(String(30), default="contract_date")  # contract_date | closing_date
    responsible_party_role = Column(String(30), nullable=True)  # buyer_agent, seller_agent, lender, etc.
    reminder_days_before = Column(Integer, default=2)
    is_conditional = Column(Boolean, default=False)
    condition_field = Column(String(50), nullable=True)  # e.g., 'financing_type'
    condition_not_value = Column(String(50), nullable=True)  # e.g., 'cash' (skip if == cash)
    sort_order = Column(Integer, default=0)

    # Relationships
    template = relationship("MilestoneTemplate", back_populates="items")

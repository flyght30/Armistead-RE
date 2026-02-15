from sqlalchemy import Column, String, Integer, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSON, TIMESTAMP
from sqlalchemy.orm import relationship
from .base_model import BaseModel


class DocumentTemplate(BaseModel):
    __tablename__ = "document_templates"

    name = Column(String(200), nullable=False)
    document_type = Column(String(50), nullable=False)  # closing_checklist, net_sheet, timeline, commission_summary, cover_letter
    template_content = Column(Text, nullable=False)  # Jinja2 template
    is_system = Column(String(10), nullable=False, default="system")  # system or custom
    agent_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # null for system templates
    variables_schema = Column(JSON, nullable=True)  # describes expected template variables

    # Relationships
    agent = relationship("User", foreign_keys=[agent_id])
    generated_docs = relationship("GeneratedDocument", back_populates="template")


class GeneratedDocument(BaseModel):
    __tablename__ = "generated_documents"

    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False)
    template_id = Column(UUID(as_uuid=True), ForeignKey("document_templates.id", ondelete="SET NULL"), nullable=True)
    document_type = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    file_url = Column(String, nullable=True)  # S3/MinIO URL of generated PDF
    html_content = Column(Text, nullable=True)  # cached HTML before PDF render
    generation_data = Column(JSON, nullable=True)  # snapshot of data used
    version = Column(Integer, nullable=False, default=1)
    generated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Relationships
    transaction = relationship("Transaction", foreign_keys=[transaction_id])
    template = relationship("DocumentTemplate", back_populates="generated_docs")
    generator = relationship("User", foreign_keys=[generated_by])

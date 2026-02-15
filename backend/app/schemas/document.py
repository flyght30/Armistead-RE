from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class DocumentTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    document_type: str
    is_system: str
    agent_id: Optional[UUID] = None
    variables_schema: Optional[dict] = None
    created_at: datetime


class GenerateDocumentRequest(BaseModel):
    document_type: str  # closing_checklist, net_sheet, timeline, commission_summary, cover_letter
    template_id: Optional[UUID] = None
    custom_data: Optional[dict] = None  # override auto-gathered data


class GeneratedDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    transaction_id: UUID
    template_id: Optional[UUID] = None
    document_type: str
    title: str
    file_url: Optional[str] = None
    version: int
    generated_by: Optional[UUID] = None
    created_at: datetime


class DocumentPreviewResponse(BaseModel):
    html_content: str
    document_type: str
    title: str

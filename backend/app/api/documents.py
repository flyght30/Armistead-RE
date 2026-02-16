from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session
from app.auth import get_current_agent_id
from app.schemas.document import (
    DocumentTemplateResponse, GenerateDocumentRequest,
    GeneratedDocumentResponse, DocumentPreviewResponse,
)
from app.services import document_service

router = APIRouter()


@router.get("/document-templates", response_model=List[DocumentTemplateResponse])
async def list_document_templates(
    db: AsyncSession = Depends(get_async_session),
    agent_id: UUID = Depends(get_current_agent_id),
):
    return await document_service.list_templates(db, agent_id=agent_id)


@router.post("/transactions/{transaction_id}/documents/generate", response_model=GeneratedDocumentResponse)
async def generate_document(
    transaction_id: UUID,
    request: GenerateDocumentRequest,
    db: AsyncSession = Depends(get_async_session),
    agent_id: UUID = Depends(get_current_agent_id),
):
    return await document_service.generate_document(transaction_id, request, db, agent_id=agent_id)


@router.post("/transactions/{transaction_id}/documents/preview", response_model=DocumentPreviewResponse)
async def preview_document(
    transaction_id: UUID,
    request: GenerateDocumentRequest,
    db: AsyncSession = Depends(get_async_session),
):
    return await document_service.preview_document(transaction_id, request, db)


@router.get("/transactions/{transaction_id}/documents", response_model=List[GeneratedDocumentResponse])
async def list_generated_documents(
    transaction_id: UUID,
    document_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_async_session),
):
    return await document_service.list_generated_documents(transaction_id, db, document_type=document_type)

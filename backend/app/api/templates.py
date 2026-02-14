from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session
from app.schemas.milestone_template import (
    MilestoneTemplateCreate,
    MilestoneTemplateUpdate,
    MilestoneTemplateResponse,
    MilestoneTemplateListResponse,
    ApplyTemplateRequest,
    ApplyTemplateResponse,
)
from app.services import template_service

router = APIRouter()


@router.get("/templates/milestones", response_model=List[MilestoneTemplateListResponse])
async def list_templates(
    state_code: Optional[str] = Query(None, description="Filter by state code (e.g., GA, AL)"),
    financing_type: Optional[str] = Query(None, description="Filter by financing type"),
    representation_side: Optional[str] = Query(None, description="Filter by representation side"),
    db: AsyncSession = Depends(get_async_session),
):
    """List available milestone templates with optional filtering."""
    return await template_service.list_templates(
        db=db,
        state_code=state_code,
        financing_type=financing_type,
        representation_side=representation_side,
    )


@router.get("/templates/milestones/{template_id}", response_model=MilestoneTemplateResponse)
async def get_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_async_session),
):
    """Get a single milestone template with all items."""
    return await template_service.get_template(template_id, db)


@router.post("/templates/milestones", response_model=MilestoneTemplateResponse)
async def create_template(
    template_create: MilestoneTemplateCreate,
    db: AsyncSession = Depends(get_async_session),
):
    """Create a new milestone template."""
    return await template_service.create_template(template_create, db)


@router.patch("/templates/milestones/{template_id}", response_model=MilestoneTemplateResponse)
async def update_template(
    template_id: UUID,
    template_update: MilestoneTemplateUpdate,
    db: AsyncSession = Depends(get_async_session),
):
    """Update a milestone template."""
    return await template_service.update_template(template_id, template_update, db)


@router.post("/transactions/{transaction_id}/apply-template", response_model=ApplyTemplateResponse)
async def apply_template(
    transaction_id: UUID,
    request: ApplyTemplateRequest,
    db: AsyncSession = Depends(get_async_session),
):
    """Apply a milestone template to a transaction, creating milestones with computed dates."""
    return await template_service.apply_template(transaction_id, request, db)

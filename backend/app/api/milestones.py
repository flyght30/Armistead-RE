from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session
from app.schemas.milestone import MilestoneCreate, MilestoneUpdate, MilestoneResponse
from app.services import milestone_service

router = APIRouter()


@router.get("/transactions/{transaction_id}/milestones", response_model=List[MilestoneResponse])
async def list_milestones(
    transaction_id: UUID,
    db: AsyncSession = Depends(get_async_session),
):
    return await milestone_service.list_milestones(transaction_id, db)


@router.post("/transactions/{transaction_id}/milestones", response_model=MilestoneResponse)
async def create_milestone(
    transaction_id: UUID,
    milestone_create: MilestoneCreate,
    db: AsyncSession = Depends(get_async_session),
):
    return await milestone_service.create_milestone(transaction_id, milestone_create, db)


@router.patch("/transactions/{transaction_id}/milestones/{milestone_id}", response_model=MilestoneResponse)
async def update_milestone(
    transaction_id: UUID,
    milestone_id: UUID,
    milestone_update: MilestoneUpdate,
    db: AsyncSession = Depends(get_async_session),
):
    return await milestone_service.update_milestone(transaction_id, milestone_id, milestone_update, db)


@router.delete("/transactions/{transaction_id}/milestones/{milestone_id}", status_code=204)
async def delete_milestone(
    transaction_id: UUID,
    milestone_id: UUID,
    db: AsyncSession = Depends(get_async_session),
):
    await milestone_service.delete_milestone(transaction_id, milestone_id, db)

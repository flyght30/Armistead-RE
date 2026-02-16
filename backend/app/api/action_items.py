from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session
from app.auth import get_current_agent_id
from app.schemas.action_item import ActionItemCreate, ActionItemUpdate, ActionItemResponse
from app.schemas.action_item import HealthScoreResponse
from app.services import action_item_service, health_score_service

router = APIRouter()


@router.get("/transactions/{transaction_id}/action-items", response_model=List[ActionItemResponse])
async def list_action_items(
    transaction_id: UUID,
    status: Optional[str] = Query(None, description="Filter by status: pending, snoozed, completed, dismissed"),
    type: Optional[str] = Query(None, description="Filter by type: milestone_due, milestone_overdue, etc."),
    db: AsyncSession = Depends(get_async_session),
):
    """List action items for a transaction."""
    return await action_item_service.list_action_items(transaction_id, db, status=status, item_type=type)


@router.post("/transactions/{transaction_id}/action-items", response_model=ActionItemResponse)
async def create_action_item(
    transaction_id: UUID,
    item_create: ActionItemCreate,
    db: AsyncSession = Depends(get_async_session),
    agent_id: UUID = Depends(get_current_agent_id),
):
    """Create a manual action item."""
    return await action_item_service.create_action_item(transaction_id, item_create, db, agent_id=agent_id)


@router.patch("/action-items/{item_id}", response_model=ActionItemResponse)
async def update_action_item(
    item_id: UUID,
    item_update: ActionItemUpdate,
    db: AsyncSession = Depends(get_async_session),
):
    """Update an action item (complete, snooze, dismiss, or edit)."""
    return await action_item_service.update_action_item(item_id, item_update, db)


@router.patch("/action-items/{item_id}/complete", response_model=ActionItemResponse)
async def complete_action_item(
    item_id: UUID,
    db: AsyncSession = Depends(get_async_session),
):
    """Mark an action item as completed."""
    return await action_item_service.complete_action_item(item_id, db)


@router.patch("/action-items/{item_id}/dismiss", response_model=ActionItemResponse)
async def dismiss_action_item(
    item_id: UUID,
    db: AsyncSession = Depends(get_async_session),
):
    """Mark an action item as dismissed."""
    return await action_item_service.dismiss_action_item(item_id, db)


@router.get("/transactions/{transaction_id}/health", response_model=HealthScoreResponse)
async def get_health_score(
    transaction_id: UUID,
    db: AsyncSession = Depends(get_async_session),
):
    """Get the health score breakdown for a transaction."""
    return await health_score_service.compute_health_score(transaction_id, db)

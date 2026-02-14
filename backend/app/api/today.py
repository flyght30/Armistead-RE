from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session
from app.schemas.action_item import TodayViewResponse
from app.services import today_service

router = APIRouter()

# Default agent ID for dev mode (matches seed data)
DEV_AGENT_ID = "00000000-0000-0000-0000-000000000001"


@router.get("/today", response_model=TodayViewResponse)
async def get_today_view(
    transaction_id: Optional[UUID] = Query(None, description="Filter to a specific transaction"),
    priority: Optional[str] = Query(None, description="Filter by priority: critical, high, medium, low"),
    filter: Optional[str] = Query(None, alias="filter", description="Filter section: overdue, due_today, coming_up, this_week"),
    db: AsyncSession = Depends(get_async_session),
):
    """Get the Today View — prioritized daily action items across all transactions."""
    # TODO: Get agent_id from auth context. Using dev agent for now.
    agent_id = UUID(DEV_AGENT_ID)
    return await today_service.get_today_view(
        agent_id=agent_id,
        db=db,
        transaction_id=transaction_id,
        priority=priority,
        filter_section=filter,
    )

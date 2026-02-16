from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session
from app.auth import get_current_agent_id
from app.schemas.action_item import TodayViewResponse
from app.services import today_service

router = APIRouter()


@router.get("/today", response_model=TodayViewResponse)
async def get_today_view(
    transaction_id: Optional[UUID] = Query(None, description="Filter to a specific transaction"),
    priority: Optional[str] = Query(None, description="Filter by priority: critical, high, medium, low"),
    filter: Optional[str] = Query(None, alias="filter", description="Filter section: overdue, due_today, coming_up, this_week"),
    db: AsyncSession = Depends(get_async_session),
    agent_id: UUID = Depends(get_current_agent_id),
):
    """Get the Today View — prioritized daily action items across all transactions."""
    return await today_service.get_today_view(
        agent_id=agent_id,
        db=db,
        transaction_id=transaction_id,
        priority=priority,
        filter_section=filter,
    )

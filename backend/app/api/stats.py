from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session
from app.services import stats_service

router = APIRouter()


@router.get("/stats/dashboard")
async def dashboard_stats(
    db: AsyncSession = Depends(get_async_session),
):
    return await stats_service.get_dashboard_stats(db)

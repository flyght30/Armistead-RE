from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session
from app.schemas.amendment import AmendmentResponse
from app.services import amendment_service

router = APIRouter()


@router.get("/transactions/{transaction_id}/amendments", response_model=List[AmendmentResponse])
async def list_amendments(
    transaction_id: UUID,
    db: AsyncSession = Depends(get_async_session),
):
    return await amendment_service.list_amendments(transaction_id, db)

from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session
from app.schemas.inspection import InspectionAnalysisResponse
from app.services import inspection_service

router = APIRouter()


@router.get("/transactions/{transaction_id}/inspections", response_model=List[InspectionAnalysisResponse])
async def list_inspections(
    transaction_id: UUID,
    db: AsyncSession = Depends(get_async_session),
):
    return await inspection_service.list_inspections(transaction_id, db)

import logging
from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session
from app.schemas.inspection import InspectionAnalysisResponse, InspectionItemResponse
from app.services import inspection_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/transactions/{transaction_id}/inspections", response_model=List[InspectionAnalysisResponse])
async def list_inspections(
    transaction_id: UUID,
    db: AsyncSession = Depends(get_async_session),
):
    return await inspection_service.list_inspections(transaction_id, db)


class UpdateRepairStatusRequest(BaseModel):
    repair_status: str


@router.patch("/inspection-items/{item_id}", response_model=InspectionItemResponse)
async def update_inspection_item(
    item_id: UUID,
    body: UpdateRepairStatusRequest,
    db: AsyncSession = Depends(get_async_session),
):
    try:
        item = await inspection_service.update_item_repair_status(item_id, body.repair_status, db)
        return InspectionItemResponse.model_validate(item)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

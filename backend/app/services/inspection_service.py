import logging
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.inspection import InspectionAnalysis
from app.schemas.inspection import InspectionAnalysisResponse

logger = logging.getLogger(__name__)


async def list_inspections(transaction_id: UUID, db: AsyncSession):
    stmt = (
        select(InspectionAnalysis)
        .where(InspectionAnalysis.transaction_id == transaction_id)
        .options(selectinload(InspectionAnalysis.items))
    )
    result = await db.execute(stmt)
    inspections = result.scalars().all()
    return [InspectionAnalysisResponse.model_validate(i) for i in inspections]


async def update_item_repair_status(item_id: UUID, repair_status: str, db: AsyncSession):
    from app.models.inspection import InspectionItem
    valid = {"pending", "in_progress", "completed"}
    if repair_status not in valid:
        raise ValueError(f"Invalid repair_status: {repair_status}. Must be one of {valid}")

    stmt = select(InspectionItem).where(InspectionItem.id == item_id)
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()
    if not item:
        raise ValueError(f"Inspection item {item_id} not found")

    item.repair_status = repair_status
    await db.commit()
    await db.refresh(item)
    return item

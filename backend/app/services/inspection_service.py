from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.inspection import InspectionAnalysis
from app.schemas.inspection import InspectionAnalysisResponse


async def list_inspections(transaction_id: UUID, db: AsyncSession):
    stmt = (
        select(InspectionAnalysis)
        .where(InspectionAnalysis.transaction_id == transaction_id)
        .options(selectinload(InspectionAnalysis.items))
    )
    result = await db.execute(stmt)
    inspections = result.scalars().all()
    return [InspectionAnalysisResponse.model_validate(i) for i in inspections]

from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.amendment import Amendment
from app.schemas.amendment import AmendmentResponse


async def list_amendments(transaction_id: UUID, db: AsyncSession):
    stmt = (
        select(Amendment)
        .where(Amendment.transaction_id == transaction_id)
        .order_by(Amendment.created_at.desc())
    )
    result = await db.execute(stmt)
    amendments = result.scalars().all()
    return [AmendmentResponse.model_validate(a) for a in amendments]

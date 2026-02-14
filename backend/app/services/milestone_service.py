from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.milestone import Milestone
from app.schemas.milestone import MilestoneCreate, MilestoneUpdate, MilestoneResponse


async def list_milestones(transaction_id: UUID, db: AsyncSession):
    stmt = (
        select(Milestone)
        .where(Milestone.transaction_id == transaction_id)
        .order_by(Milestone.sort_order)
    )
    result = await db.execute(stmt)
    milestones = result.scalars().all()
    return [MilestoneResponse.model_validate(m) for m in milestones]


async def create_milestone(transaction_id: UUID, milestone_create: MilestoneCreate, db: AsyncSession):
    new_milestone = Milestone(
        transaction_id=transaction_id,
        type=milestone_create.type,
        title=milestone_create.title,
        due_date=milestone_create.due_date,
        status=milestone_create.status,
        responsible_party_role=milestone_create.responsible_party_role,
        notes=milestone_create.notes,
        reminder_days_before=milestone_create.reminder_days_before,
        sort_order=milestone_create.sort_order,
    )
    db.add(new_milestone)
    await db.commit()
    await db.refresh(new_milestone)
    return MilestoneResponse.model_validate(new_milestone)


async def update_milestone(transaction_id: UUID, milestone_id: UUID, milestone_update: MilestoneUpdate, db: AsyncSession):
    milestone = await db.get(Milestone, milestone_id)
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")
    update_data = milestone_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(milestone, field, value)
    await db.commit()
    await db.refresh(milestone)
    return MilestoneResponse.model_validate(milestone)


async def delete_milestone(transaction_id: UUID, milestone_id: UUID, db: AsyncSession):
    milestone = await db.get(Milestone, milestone_id)
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")
    await db.delete(milestone)
    await db.commit()

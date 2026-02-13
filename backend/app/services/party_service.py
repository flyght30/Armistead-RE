from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session
from app.models.party import Party
from app.schemas.party import PartyCreate, PartyUpdate, PartyResponse

async def create_party(id: UUID, party_create: PartyCreate, db: AsyncSession = Depends(get_async_session)):
    new_party = Party(
        name=party_create.name,
        role=party_create.role,
        contact_info=party_create.contact_info,
        transaction_id=id
    )
    db.add(new_party)
    await db.commit()
    await db.refresh(new_party)

    return PartyResponse.from_orm(new_party)

async def update_party(id: UUID, party_id: UUID, party_update: PartyUpdate, db: AsyncSession = Depends(get_async_session)):
    party = await db.get(Party, party_id)
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")

    for field in party_update.dict(exclude_unset=True):
        setattr(party, field, party_update.dict()[field])

    await db.commit()
    await db.refresh(party)

    return PartyResponse.from_orm(party)

async def delete_party(id: UUID, party_id: UUID, db: AsyncSession = Depends(get_async_session)):
    party = await db.get(Party, party_id)
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")

    await db.delete(party)
    await db.commit()

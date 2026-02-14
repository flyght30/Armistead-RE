from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.party import Party
from app.schemas.party import PartyCreate, PartyUpdate, PartyResponse


async def create_party(transaction_id: UUID, party_create: PartyCreate, db: AsyncSession):
    new_party = Party(
        name=party_create.name,
        role=party_create.role,
        email=party_create.email,
        phone=party_create.phone,
        company=party_create.company,
        is_primary=party_create.is_primary,
        transaction_id=transaction_id,
    )
    db.add(new_party)
    await db.commit()
    await db.refresh(new_party)

    return PartyResponse.model_validate(new_party)


async def update_party(transaction_id: UUID, party_id: UUID, party_update: PartyUpdate, db: AsyncSession):
    party = await db.get(Party, party_id)
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")

    update_data = party_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(party, field, value)

    await db.commit()
    await db.refresh(party)

    return PartyResponse.model_validate(party)


async def delete_party(transaction_id: UUID, party_id: UUID, db: AsyncSession):
    party = await db.get(Party, party_id)
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")

    await db.delete(party)
    await db.commit()

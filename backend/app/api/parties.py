from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session
from app.schemas.party import PartyCreate, PartyUpdate, PartyResponse
from app.services import party_service

router = APIRouter()


@router.post("/transactions/{transaction_id}/parties", response_model=PartyResponse)
async def create_party(
    transaction_id: UUID,
    party_create: PartyCreate,
    db: AsyncSession = Depends(get_async_session),
):
    return await party_service.create_party(transaction_id, party_create, db)


@router.patch("/transactions/{transaction_id}/parties/{party_id}", response_model=PartyResponse)
async def update_party(
    transaction_id: UUID,
    party_id: UUID,
    party_update: PartyUpdate,
    db: AsyncSession = Depends(get_async_session),
):
    return await party_service.update_party(transaction_id, party_id, party_update, db)


@router.delete("/transactions/{transaction_id}/parties/{party_id}", status_code=204)
async def delete_party(
    transaction_id: UUID,
    party_id: UUID,
    db: AsyncSession = Depends(get_async_session),
):
    await party_service.delete_party(transaction_id, party_id, db)

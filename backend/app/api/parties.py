from fastapi import APIRouter, Depends
from app.services.party_service import party_service
from app.schemas.party import PartyCreate, PartyUpdate, PartyResponse

router = APIRouter()

@router.post("/api/transactions/{id}/parties", response_model=PartyResponse)
async def create_party(id: UUID, party_create: PartyCreate):
    return await party_service.create_party(id, party_create)

@router.patch("/api/transactions/{id}/parties/{party_id}", response_model=PartyResponse)
async def update_party(id: UUID, party_id: UUID, party_update: PartyUpdate):
    return await party_service.update_party(id, party_id, party_update)

@router.delete("/api/transactions/{id}/parties/{party_id}")
async def delete_party(id: UUID, party_id: UUID):
    await party_service.delete_party(id, party_id)

from fastapi import APIRouter, Depends
from app.services.transaction_service import transaction_service
from app.services.party_service import party_service
from app.schemas.common import PaginationParams
from app.schemas.transaction import TransactionCreate, TransactionUpdate, TransactionResponse, TransactionList
from app.schemas.party import PartyCreate, PartyUpdate, PartyResponse

router = APIRouter()

@router.post("/api/transactions", response_model=TransactionResponse)
async def create_transaction(transaction: TransactionCreate):
    return await transaction_service.create_transaction(transaction)

@router.get("/api/transactions", response_model=TransactionList)
async def list_transactions(pagination_params: PaginationParams):
    return await transaction_service.list_transactions(pagination_params)

@router.get("/api/transactions/{id}", response_model=TransactionResponse)
async def get_transaction(id: UUID):
    return await transaction_service.get_transaction(id)

@router.patch("/api/transactions/{id}", response_model=TransactionResponse)
async def update_transaction(id: UUID, transaction_update: TransactionUpdate):
    return await transaction_service.update_transaction(id, transaction_update)

@router.delete("/api/transactions/{id}")
async def delete_transaction(id: UUID):
    await transaction_service.soft_delete_transaction(id)

@router.post("/api/transactions/{id}/parse")
async def parse_contract(id: UUID):
    await transaction_service.parse_contract(id)
    return APIResponse(success=True, message="Contract parsing initiated")

@router.post("/api/transactions/{id}/confirm")
async def confirm_transaction(id: UUID):
    await transaction_service.confirm_transaction(id)
    return APIResponse(success=True, message="Transaction confirmed and activated")

@router.post("/api/transactions/{id}/parties", response_model=PartyResponse)
async def create_party(id: UUID, party_create: PartyCreate):
    return await party_service.create_party(id, party_create)

@router.patch("/api/transactions/{id}/parties/{party_id}", response_model=PartyResponse)
async def update_party(id: UUID, party_id: UUID, party_update: PartyUpdate):
    return await party_service.update_party(id, party_id, party_update)

@router.delete("/api/transactions/{id}/parties/{party_id}")
async def delete_party(id: UUID, party_id: UUID):
    await party_service.delete_party(id, party_id)

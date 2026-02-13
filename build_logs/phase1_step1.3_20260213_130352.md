# Phase 1 — Step 1.3: Pydantic schemas & API endpoints (transactions, parties)
**Generated:** 2026-02-13T13:03:52.917769

===FILE: backend/app/schemas/common.py===
from pydantic import BaseModel, Field
from typing import Optional

class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    limit: int = Field(10, ge=1, le=100)

class APIResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    data: Optional[any] = None

===END FILE===

===FILE: backend/app/schemas/transaction.py===
from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from .common import PaginationParams

class TransactionBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: str
    created_by_id: UUID
    updated_by_id: UUID

class TransactionCreate(TransactionBase):
    file_path: str

class TransactionUpdate(TransactionBase):
    pass

class TransactionResponse(TransactionBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    parties: List['PartyResponse']

class TransactionList(BaseModel):
    items: List[TransactionResponse]
    pagination: PaginationParams

===END FILE===

===FILE: backend/app/schemas/party.py===
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime
from .common import PaginationParams

class PartyBase(BaseModel):
    name: str
    role: str
    contact_info: Optional[str] = None

class PartyCreate(PartyBase):
    transaction_id: UUID

class PartyUpdate(PartyBase):
    pass

class PartyResponse(PartyBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

===END FILE===

===FILE: backend/app/api/__init__.py===
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
===END FILE===

===FILE: backend/app/api/transactions.py===
from fastapi import APIRouter, Depends
from app.services.transaction_service import transaction_service
from app.schemas.common import PaginationParams
from app.schemas.transaction import TransactionCreate, TransactionUpdate, TransactionResponse, TransactionList

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
===END FILE===

===FILE: backend/app/api/parties.py===
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
===END FILE===

===FILE: backend/app/services/transaction_service.py===
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionCreate, TransactionUpdate, TransactionResponse
from app.services.party_service import create_party as party_create_service
from app.agents.contract_parser import parse_contract as contract_parser_agent
from app.agents.email_sender import send_email as email_sender_agent

async def create_transaction(transaction_create: TransactionCreate, db: AsyncSession = Depends(get_async_session)):
    new_transaction = Transaction(
        title=transaction_create.title,
        description=transaction_create.description,
        status="draft",
        created_by_id=transaction_create.created_by_id,
        updated_by_id=transaction_create.updated_by_id
    )
    db.add(new_transaction)
    await db.commit()
    await db.refresh(new_transaction)

    # Create parties if any are provided in the request
    for party_data in transaction_create.parties or []:
        await party_create_service(id=new_transaction.id, party_create=party_data, db=db)

    return TransactionResponse.from_orm(new_transaction)

async def list_transactions(pagination_params: PaginationParams, db: AsyncSession = Depends(get_async_session)):
    # Implement pagination logic here
    pass

async def get_transaction(id: UUID, db: AsyncSession = Depends(get_async_session)):
    transaction = await db.get(Transaction, id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return TransactionResponse.from_orm(transaction)

async def update_transaction(id: UUID, transaction_update: TransactionUpdate, db: AsyncSession = Depends(get_async_session)):
    transaction = await db.get(Transaction, id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    for field in transaction_update.dict(exclude_unset=True):
        setattr(transaction, field, transaction_update.dict()[field])

    # Log amendments
    amendment = Amendment(
        transaction_id=id,
        field_changed=", ".join([f"{k}={v}" for k, v in transaction_update.dict().items()]),
        old_value=transaction.__dict__,
        new_value=transaction_update.dict(),
        changed_by_id=transaction.updated_by_id,
        notification_sent=False
    )
    db.add(amendment)
    await db.commit()
    await db.refresh(amendment)

    return TransactionResponse.from_orm(transaction)

async def soft_delete_transaction(id: UUID, db: AsyncSession = Depends(get_async_session)):
    transaction = await db.get(Transaction, id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    transaction.status = "deleted"
    await db.commit()
    await db.refresh(transaction)

async def parse_contract(id: UUID, db: AsyncSession = Depends(get_async_session)):
    transaction = await db.get(Transaction, id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    contract_data = await contract_parser_agent(transaction.file_path)
    # Update transaction fields based on parsed data
    for key, value in contract_data.items():
        setattr(transaction, key, value)

    await db.commit()
    await db.refresh(transaction)

async def confirm_transaction(id: UUID, db: AsyncSession = Depends(get_async_session)):
    transaction = await db.get(Transaction, id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    transaction.status = "confirmed"
    await db.commit()
    await db.refresh(transaction)

    # Send confirmation email
    await email_sender_agent(
        recipient_email=transaction.created_by.email,
        subject="Transaction Confirmed",
        body=f"Your transaction {transaction.title} has been confirmed and activated."
    )
===END FILE===

===FILE: backend/app/services/party_service.py===
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
===END FILE===

===FILE: backend/app/agents/contract_parser.py===
import asyncio
from anthropic import AnthropicClient, ClaudeAPIError
from app.config import settings

client = AnthropicClient(api_key=settings.clau

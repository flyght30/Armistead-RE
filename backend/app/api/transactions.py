from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session
from app.schemas.common import PaginationParams, APIResponse
from app.schemas.transaction import (
    TransactionCreate,
    TransactionUpdate,
    TransactionResponse,
    TransactionDetailResponse,
    TransactionList,
)
from app.services import transaction_service

router = APIRouter()


@router.post("/transactions", response_model=TransactionResponse)
async def create_transaction(
    transaction: TransactionCreate,
    db: AsyncSession = Depends(get_async_session),
):
    return await transaction_service.create_transaction(transaction, db)


@router.get("/transactions", response_model=TransactionList)
async def list_transactions(
    page: int = 1,
    limit: int = 10,
    db: AsyncSession = Depends(get_async_session),
):
    pagination = PaginationParams(page=page, limit=limit)
    return await transaction_service.list_transactions(pagination, db)


@router.get("/transactions/{id}", response_model=TransactionDetailResponse)
async def get_transaction(
    id: UUID,
    db: AsyncSession = Depends(get_async_session),
):
    return await transaction_service.get_transaction(id, db)


@router.patch("/transactions/{id}", response_model=TransactionResponse)
async def update_transaction(
    id: UUID,
    transaction_update: TransactionUpdate,
    db: AsyncSession = Depends(get_async_session),
):
    return await transaction_service.update_transaction(id, transaction_update, db)


@router.delete("/transactions/{id}", status_code=204)
async def delete_transaction(
    id: UUID,
    db: AsyncSession = Depends(get_async_session),
):
    await transaction_service.soft_delete_transaction(id, db)


@router.post("/transactions/{id}/parse")
async def parse_contract(
    id: UUID,
    db: AsyncSession = Depends(get_async_session),
):
    await transaction_service.parse_contract(id, db)
    return APIResponse(success=True, message="Contract parsing initiated")


@router.post("/transactions/{id}/confirm")
async def confirm_transaction(
    id: UUID,
    db: AsyncSession = Depends(get_async_session),
):
    await transaction_service.confirm_transaction(id, db)
    return APIResponse(success=True, message="Transaction confirmed and activated")

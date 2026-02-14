import logging
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.transaction import Transaction
from app.models.amendment import Amendment
from app.models.inspection import InspectionAnalysis
from app.schemas.common import PaginationParams
from app.schemas.transaction import TransactionCreate, TransactionUpdate, TransactionResponse, TransactionDetailResponse, TransactionList
from app.services.party_service import create_party as party_create_service
from app.agents.contract_parser import parse_contract as contract_parser_agent
from app.agents.email_sender import send_email as email_sender_agent

logger = logging.getLogger(__name__)


async def create_transaction(transaction_create: TransactionCreate, db: AsyncSession):
    new_transaction = Transaction(
        agent_id=transaction_create.agent_id,
        status="draft",
        representation_side=transaction_create.representation_side,
        financing_type=transaction_create.financing_type,
        property_address=transaction_create.property_address,
        property_city=transaction_create.property_city,
        property_state=transaction_create.property_state,
        property_zip=transaction_create.property_zip,
        purchase_price=transaction_create.purchase_price,
        earnest_money_amount=transaction_create.earnest_money_amount,
        closing_date=transaction_create.closing_date,
        contract_document_url=transaction_create.contract_document_url,
        special_stipulations=transaction_create.special_stipulations,
    )
    db.add(new_transaction)
    await db.commit()
    await db.refresh(new_transaction, ["parties"])

    return TransactionResponse.model_validate(new_transaction)


async def list_transactions(pagination_params: PaginationParams, db: AsyncSession):
    offset = (pagination_params.page - 1) * pagination_params.limit
    stmt = (
        select(Transaction)
        .where(Transaction.status != "deleted")
        .options(selectinload(Transaction.parties))
        .offset(offset)
        .limit(pagination_params.limit)
    )
    result = await db.execute(stmt)
    transactions = result.scalars().all()

    return TransactionList(
        items=[TransactionResponse.model_validate(t) for t in transactions],
        pagination=pagination_params,
    )


async def get_transaction(id: UUID, db: AsyncSession):
    stmt = (
        select(Transaction)
        .where(Transaction.id == id)
        .options(
            selectinload(Transaction.parties),
            selectinload(Transaction.milestones),
            selectinload(Transaction.amendments),
            selectinload(Transaction.files),
            selectinload(Transaction.inspection_analyses).selectinload(InspectionAnalysis.items),
            selectinload(Transaction.communications),
        )
    )
    result = await db.execute(stmt)
    transaction = result.scalar_one_or_none()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return TransactionDetailResponse.model_validate(transaction)


async def update_transaction(id: UUID, transaction_update: TransactionUpdate, db: AsyncSession):
    transaction = await db.get(Transaction, id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    update_data = transaction_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(transaction, field, value)

    # Log amendment
    amendment = Amendment(
        transaction_id=id,
        field_changed=", ".join(update_data.keys()),
        old_value={},  # TODO: capture old values before update
        new_value=update_data,
        reason="Field update via API",
        changed_by_id=transaction.agent_id,
        notification_sent=False,
    )
    db.add(amendment)
    await db.commit()
    await db.refresh(transaction, ["parties"])

    return TransactionResponse.model_validate(transaction)


async def soft_delete_transaction(id: UUID, db: AsyncSession):
    transaction = await db.get(Transaction, id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    transaction.status = "deleted"
    await db.commit()


async def parse_contract(id: UUID, db: AsyncSession):
    transaction = await db.get(Transaction, id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    contract_data = await contract_parser_agent(transaction.contract_document_url)
    # Update transaction fields based on parsed data
    if contract_data and isinstance(contract_data, dict):
        allowed_fields = {
            "property_address", "property_city", "property_state", "property_zip",
            "purchase_price", "earnest_money_amount", "financing_type",
            "special_stipulations", "ai_extraction_confidence",
        }
        for key, value in contract_data.items():
            if key in allowed_fields:
                setattr(transaction, key, value)

    await db.commit()
    await db.refresh(transaction)


async def confirm_transaction(id: UUID, db: AsyncSession):
    transaction = await db.get(Transaction, id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    transaction.status = "confirmed"
    await db.commit()
    await db.refresh(transaction, ["agent"])

    # Send confirmation email
    try:
        await email_sender_agent(
            recipient_email=transaction.agent.email,
            subject="Transaction Confirmed",
            body=f"Your transaction for {transaction.property_address or 'N/A'} has been confirmed and activated.",
        )
    except Exception:
        logger.exception("Failed to send confirmation email for transaction %s", id)

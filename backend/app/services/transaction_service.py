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

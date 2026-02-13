from typing import Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.database import get_async_session
from app.models.transaction import Transaction
from app.schemas.contract_parsing import ParseResponse
from app.services.storage_service import upload_file
from app.agents.contract_parser import parse_contract

async def parse_and_save_transaction(file: UploadFile, db: AsyncSession = Depends(get_async_session)) -> dict:
    file_id = await upload_file(file, db)
    
    parsed_data = await parse_contract(file.filename)
    
    new_transaction = Transaction(
        id=uuid.uuid4(),
        title=file.filename,
        status="pending",
        file_path=file.filename,
        created_by_id=settings.admin_user_id  # Assuming admin user ID is set in settings
    )
    db.add(new_transaction)
    await db.commit()
    await db.refresh(new_transaction)

    for party_data in parsed_data.data.parties:
        new_party = Party(
            id=uuid.uuid4(),
            name=party_data.name,
            role=party_data.role,
            contact_info=party_data.contact_info,
            transaction_id=new_transaction.id
        )
        db.add(new_party)
        await db.commit()
        await db.refresh(new_party)

    return {
        "status": parsed_data.status,
        "data": new_transaction.dict(),
        "confidence_scores": parsed_data.confidence_scores,
        "detected_features": parsed_data.detected_features
    }

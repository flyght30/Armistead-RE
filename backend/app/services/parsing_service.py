import logging
import uuid
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.transaction import Transaction
from app.models.party import Party
from app.schemas.contract_parsing import ParseResponse
from app.services.storage_service import upload_file
from app.agents.contract_parser import parse_contract

logger = logging.getLogger(__name__)


async def parse_and_save_transaction(
    file: UploadFile,
    agent_id: uuid.UUID,
    db: AsyncSession,
) -> dict:
    """Upload a contract file, parse it via AI, and create a transaction with parties."""
    file_id = await upload_file(file, db)

    parsed_data = await parse_contract(file.filename)

    new_transaction = Transaction(
        agent_id=agent_id,
        status="pending_review",
        representation_side="buyer",  # Will be updated from parsed data
        property_address=parsed_data.get("property_details", {}).get("address"),
        property_city=parsed_data.get("property_details", {}).get("city"),
        property_state=parsed_data.get("property_details", {}).get("state"),
        property_zip=parsed_data.get("property_details", {}).get("zip_code"),
        purchase_price=parsed_data.get("financial_terms", {}).get("purchase_price"),
        financing_type=parsed_data.get("financial_terms", {}).get("financing_type"),
        contract_document_url=file.filename,
        ai_extraction_confidence=parsed_data.get("confidence_scores"),
    )
    db.add(new_transaction)
    await db.commit()
    await db.refresh(new_transaction)

    # Create parties from parsed data
    for party_data in parsed_data.get("parties", []):
        contact = party_data.get("contact_info", {})
        new_party = Party(
            name=party_data.get("name", "Unknown"),
            role=party_data.get("role", "unknown"),
            email=contact.get("email", ""),
            phone=contact.get("phone"),
            company=contact.get("company"),
            transaction_id=new_transaction.id,
        )
        db.add(new_party)

    await db.commit()

    return {
        "status": "success",
        "transaction_id": str(new_transaction.id),
        "confidence_scores": parsed_data.get("confidence_scores", {}),
        "detected_features": parsed_data.get("detected_features", []),
    }

import logging
import os
import tempfile
from uuid import UUID
from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session
from app.models.file import File as FileModel
from app.models.transaction import Transaction
from app.models.party import Party
from app.schemas.file import FileResponse
from app.services.storage_service import upload_file, get_file_url
from app.agents.contract_parser import parse_contract
from app.services.template_service import apply_template, list_templates
from app.schemas.milestone_template import ApplyTemplateRequest
from app.services.health_score_service import compute_health_score

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/transactions/{transaction_id}/files", response_model=List[FileResponse])
async def list_files(
    transaction_id: UUID,
    db: AsyncSession = Depends(get_async_session),
):
    stmt = select(FileModel).where(FileModel.transaction_id == transaction_id)
    result = await db.execute(stmt)
    files = result.scalars().all()
    return [FileResponse.model_validate(f) for f in files]


@router.post("/transactions/{transaction_id}/files", response_model=FileResponse)
async def upload_transaction_file(
    transaction_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_async_session),
):
    file_id = await upload_file(file, db)
    file_record = await db.get(FileModel, file_id)
    if file_record:
        file_record.transaction_id = transaction_id
        await db.commit()
        await db.refresh(file_record)
    return FileResponse.model_validate(file_record)


@router.post("/transactions/{transaction_id}/files/upload-contract")
async def upload_and_parse_contract(
    transaction_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Upload a contract PDF, parse it via Claude AI, and update the existing
    transaction with extracted data including parties and milestone templates.
    """
    transaction = await db.get(Transaction, transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Upload the file to storage and link it
    file_id = await upload_file(file, db)
    file_record = await db.get(FileModel, file_id)
    if file_record:
        file_record.transaction_id = transaction_id
        await db.commit()
        await db.refresh(file_record)

    # Write to temp file for PDF parsing
    await file.seek(0)
    contents = await file.read()
    suffix = "." + (file.filename.split(".")[-1] if file.filename else "pdf")
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        parsed_data = await parse_contract(tmp_path)
    finally:
        os.unlink(tmp_path)

    # Update transaction with parsed fields
    prop = parsed_data.get("property_details", {})
    fin = parsed_data.get("financial_terms", {})
    dates = parsed_data.get("dates", {})

    if prop.get("address"):
        transaction.property_address = prop["address"]
    if prop.get("city"):
        transaction.property_city = prop["city"]
    if prop.get("state"):
        transaction.property_state = prop["state"]
    if prop.get("zip_code"):
        transaction.property_zip = prop["zip_code"]
    if fin.get("purchase_price"):
        transaction.purchase_price = fin["purchase_price"]
    if fin.get("financing_type"):
        transaction.financing_type = fin["financing_type"]

    closing_date_str = dates.get("closing_date")
    if closing_date_str:
        try:
            parsed_closing = datetime.fromisoformat(closing_date_str)
            if parsed_closing.tzinfo is None:
                parsed_closing = parsed_closing.replace(tzinfo=timezone.utc)
            transaction.closing_date = parsed_closing
        except (ValueError, TypeError):
            logger.warning("Could not parse closing date: %s", closing_date_str)

    if file_record:
        transaction.contract_document_url = file_record.url
    transaction.ai_extraction_confidence = parsed_data.get("confidence_scores")

    await db.commit()
    await db.refresh(transaction)

    # Auto-create parties from parsed data
    parties_created = []
    for party_data in parsed_data.get("parties", []):
        contact = party_data.get("contact_info", {})
        new_party = Party(
            name=party_data.get("name", "Unknown"),
            role=party_data.get("role", "unknown"),
            email=contact.get("email", ""),
            phone=contact.get("phone"),
            company=contact.get("company"),
            transaction_id=transaction_id,
        )
        db.add(new_party)
        parties_created.append({"name": new_party.name, "role": new_party.role, "email": new_party.email})
    await db.commit()

    # Auto-apply milestone template based on property state
    template_applied = None
    if transaction.property_state:
        templates = await list_templates(db, state_code=transaction.property_state, financing_type=transaction.financing_type)
        if templates:
            selected = templates[0]
            for t in templates:
                if t.is_default:
                    selected = t
                    break
            apply_request = ApplyTemplateRequest(
                template_id=selected.id,
                contract_execution_date=transaction.contract_execution_date or datetime.now(timezone.utc),
                closing_date=transaction.closing_date,
            )
            template_result = await apply_template(transaction_id, apply_request, db)
            template_applied = {
                "template_id": str(selected.id),
                "template_name": selected.name,
                "milestones_created": template_result.milestones_created,
                "milestones_skipped": template_result.milestones_skipped,
            }

    # Compute health score
    health_result = await compute_health_score(transaction_id, db)

    return {
        "status": "success",
        "transaction_id": str(transaction_id),
        "file_id": str(file_id),
        "parsed_data": parsed_data,
        "parties_created": parties_created,
        "template_applied": template_applied,
        "health_score": health_result.score,
        "confidence_scores": parsed_data.get("confidence_scores", {}),
        "detected_features": parsed_data.get("detected_features", []),
    }

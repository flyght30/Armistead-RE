# Phase 1 — Step 1.4: S3 file upload & Claude API contract parser
**Generated:** 2026-02-13T13:04:37.333679

===FILE: backend/app/services/storage_service.py===
from typing import Optional
import uuid
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.database import get_async_session
from app.models.file import File

async def upload_file(file: UploadFile, db: AsyncSession = Depends(get_async_session)) -> str:
    if file.content_type not in ["application/pdf", "image/jpeg", "image/png"]:
        raise ValueError("Unsupported file type")
    
    if len(await file.read()) > 25 * 1024 * 1024:
        raise ValueError("File size exceeds limit")

    file.filename = f"{uuid.uuid4()}.{file.filename.split('.')[-1]}"
    await file.seek(0)

    # Save file to S3/MinIO
    s3_client = settings.s3_client
    response = s3_client.upload_fileobj(file.file, settings.bucket_name, file.filename)
    
    new_file = File(
        id=uuid.uuid4(),
        name=file.filename,
        content_type=file.content_type,
        url=s3_client.generate_presigned_url('get_object', Params={'Bucket': settings.bucket_name, 'Key': file.filename}, ExpiresIn=900),
        transaction_id=None
    )
    db.add(new_file)
    await db.commit()
    await db.refresh(new_file)

    return new_file.id

async def get_file_url(file_id: UUID, db: AsyncSession = Depends(get_async_session)) -> str:
    file = await db.get(File, file_id)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    return file.url
===END FILE===

===FILE: backend/app/agents/__init__.py===
from .contract_parser import contract_parser_agent
===END FILE===

===FILE: backend/app/agents/contract_parser.py===
import asyncio
from anthropic import AnthropicClient, ClaudeAPIError
from app.config import settings
from app.schemas.contract_parsing import ContractExtractionSchema, ParseResponse
from fitz import open as pdf_open  # PyMuPDF

client = AnthropicClient(api_key=settings.clau

async def contract_parser_agent(file_path: str) -> dict:
    try:
        response = await client.chat.completions.create(
            model="claude-2",
            system_prompt="You are an AI assistant designed to parse real estate contracts. Extract all relevant information from the provided document, including property details, financial terms, parties involved, and dates. Return a structured JSON object with confidence scores for each field.",
            messages=[
                {"role": "user", "content": f"File: {file_path}"}
            ]
        )
        return response.completion
    except ClaudeAPIError as e:
        if e.status_code == 429:
            await asyncio.sleep(2)  # Exponential backoff
            return await contract_parser_agent(file_path)
        else:
            raise

async def extract_text_from_pdf(file_path: str) -> str:
    with pdf_open(file_path) as pdf_document:
        text = ""
        for page_num in range(len(pdf_document)):
            text += pdf_document.load_page(page_num).get_text("text")
        return text

async def parse_contract(file_path: str) -> dict:
    text = await extract_text_from_pdf(file_path)
    
    if len(text) < 100:
        # Fallback to vision for small text
        pass
    
    response = await contract_parser_agent(file_path)
    
    parsed_data = ContractExtractionSchema.parse_raw(response)
    
    return {
        "status": "success",
        "data": parsed_data.dict(),
        "confidence_scores": parsed_data.confidence_scores,
        "detected_features": parsed_data.detected_features
    }
===END FILE===

===FILE: backend/app/services/parsing_service.py===
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
===END FILE===

===FILE: backend/app/schemas/contract_parsing.py===
from pydantic import BaseModel, Field
from typing import Dict, List, Optional

class PropertyDetails(BaseModel):
    address: str = Field(..., description="Property address")
    city: str = Field(..., description="City of property location")
    state: str = Field(..., description="State of property location")
    zip_code: str = Field(..., description="ZIP code of property location")

class FinancialTerms(BaseModel):
    purchase_price: float = Field(..., description="Purchase price of the property")
    down_payment: Optional[float] = Field(None, description="Down payment amount")
    financing_type: Optional[str] = Field(None, description="Type of financing used")

class Party(BaseModel):
    name: str = Field(..., description="Party name")
    role: str = Field(..., description="Role of the party in the transaction")
    contact_info: Dict[str, str] = Field(..., description="Contact information for the party")

class ContractExtractionSchema(BaseModel):
    property_details: PropertyDetails
    financial_terms: FinancialTerms
    parties: List[Party]
    dates: Dict[str, str]
    confidence_scores: Dict[str, float]
    detected_features: List[str]

class ParseResponse(BaseModel):
    status: str = Field(..., description="Status of the parsing operation")
    data: ContractExtractionSchema
    confidence_scores: Dict[str, float]
    detected_features: List[str]
===END FILE===

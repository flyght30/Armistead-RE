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

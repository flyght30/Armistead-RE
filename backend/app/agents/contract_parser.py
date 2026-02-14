import asyncio
import base64
import json
import logging
from typing import Dict, List, Optional

import anthropic
import fitz  # PyMuPDF

from app.config import Settings
from app.schemas.contract_parsing import ContractExtractionSchema

logger = logging.getLogger(__name__)
settings = Settings()

client = anthropic.AsyncAnthropic(api_key=settings.claude_api_key)

SYSTEM_PROMPT = """You are an AI assistant designed to parse real estate contracts.
Extract all relevant information from the provided document text, including:
- Property details (address, city, state, zip)
- Financial terms (purchase price, down payment, financing type)
- All parties involved (names, roles, contact info)
- Important dates (closing date, inspection deadlines, etc.)

Return a structured JSON object matching this schema:
{
  "property_details": {"address": "", "city": "", "state": "", "zip_code": ""},
  "financial_terms": {"purchase_price": 0, "down_payment": null, "financing_type": ""},
  "parties": [{"name": "", "role": "", "contact_info": {"email": "", "phone": ""}}],
  "dates": {"closing_date": "", "inspection_deadline": ""},
  "confidence_scores": {"property_details": 0.0, "financial_terms": 0.0, "parties": 0.0, "dates": 0.0},
  "detected_features": ["feature1", "feature2"]
}

Return ONLY valid JSON, no markdown or explanations."""

MAX_RETRIES = 3
BASE_DELAY = 1.0  # seconds


async def _call_claude_with_retry(
    messages: list,
    system: str = SYSTEM_PROMPT,
    max_retries: int = MAX_RETRIES,
) -> str:
    """Call the Anthropic API with exponential backoff retry logic."""
    for attempt in range(max_retries):
        try:
            response = await client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=system,
                messages=messages,
            )
            return response.content[0].text
        except anthropic.RateLimitError:
            delay = BASE_DELAY * (2 ** attempt)
            logger.warning("Rate limited (attempt %d/%d). Retrying in %.1fs...", attempt + 1, max_retries, delay)
            await asyncio.sleep(delay)
        except anthropic.APIStatusError as e:
            logger.error("Anthropic API error (status %d): %s", e.status_code, str(e))
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(BASE_DELAY * (2 ** attempt))
        except anthropic.APIConnectionError:
            logger.error("Connection error (attempt %d/%d)", attempt + 1, max_retries)
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(BASE_DELAY * (2 ** attempt))

    raise RuntimeError(f"Failed to get response after {max_retries} retries")


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text content from a PDF file using PyMuPDF."""
    try:
        with fitz.open(file_path) as pdf_document:
            text = ""
            for page_num in range(len(pdf_document)):
                page = pdf_document.load_page(page_num)
                text += page.get_text("text")
            return text
    except Exception:
        logger.exception("Failed to extract text from PDF: %s", file_path)
        return ""


def extract_images_from_pdf(file_path: str) -> List[str]:
    """Extract page images from a PDF as base64-encoded PNGs for vision fallback."""
    images = []
    try:
        with fitz.open(file_path) as pdf_document:
            for page_num in range(min(len(pdf_document), 20)):  # Cap at 20 pages
                page = pdf_document.load_page(page_num)
                pix = page.get_pixmap(dpi=150)
                img_bytes = pix.tobytes("png")
                images.append(base64.b64encode(img_bytes).decode("utf-8"))
    except Exception:
        logger.exception("Failed to extract images from PDF: %s", file_path)
    return images


async def _parse_with_text(text: str) -> str:
    """Parse contract using extracted text content."""
    messages = [
        {
            "role": "user",
            "content": f"Parse the following real estate contract and extract all relevant information:\n\n{text}",
        }
    ]
    return await _call_claude_with_retry(messages)


async def _parse_with_vision(images: List[str]) -> str:
    """Parse contract using vision on page images (fallback for scanned PDFs)."""
    content = [
        {"type": "text", "text": "Parse this real estate contract from the page images and extract all relevant information:"},
    ]
    for img_b64 in images:
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": img_b64,
            },
        })

    messages = [{"role": "user", "content": content}]
    return await _call_claude_with_retry(messages)


async def parse_contract(file_path: str) -> dict:
    """
    Main entry point: parse a contract PDF and return structured data.
    Uses text extraction first, falls back to vision for scanned/image-heavy PDFs.
    """
    if not file_path:
        raise ValueError("file_path is required")

    # Step 1: Try text extraction
    text = extract_text_from_pdf(file_path)

    raw_response: Optional[str] = None

    if len(text.strip()) >= 100:
        # Sufficient text extracted — use text-based parsing
        logger.info("Using text-based parsing for %s (%d chars)", file_path, len(text))
        raw_response = await _parse_with_text(text)
    else:
        # Fallback to vision for scanned PDFs or image-based contracts
        logger.info("Text too short (%d chars) for %s — falling back to vision", len(text), file_path)
        images = extract_images_from_pdf(file_path)
        if not images:
            raise ValueError(f"Could not extract text or images from PDF: {file_path}")
        raw_response = await _parse_with_vision(images)

    # Step 2: Parse and validate the response
    try:
        # Strip markdown code fences if present
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]

        parsed_json = json.loads(cleaned)
        # Validate against schema
        validated = ContractExtractionSchema.model_validate(parsed_json)
        return validated.model_dump()
    except (json.JSONDecodeError, Exception) as e:
        logger.error("Failed to parse AI response as JSON: %s", str(e))
        logger.debug("Raw response: %s", raw_response[:500])
        # Return a minimal valid structure on parse failure
        return {
            "property_details": {"address": "", "city": "", "state": "", "zip_code": ""},
            "financial_terms": {"purchase_price": 0, "down_payment": None, "financing_type": ""},
            "parties": [],
            "dates": {},
            "confidence_scores": {},
            "detected_features": ["parse_error"],
        }

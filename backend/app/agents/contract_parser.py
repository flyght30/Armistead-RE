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

SYSTEM_PROMPT = """You are an expert real estate transaction coordinator AI that parses purchase contracts.
You specialize in residential real estate contracts from the Southeastern US (Alabama, Georgia, etc.),
including LCAR, GAR, and standard REALTOR association forms.

Extract ALL information from the provided contract. Be thorough — agents depend on this data.

Return a JSON object with this exact structure:

{
  "property_details": {
    "address": "street address only",
    "city": "city name",
    "state": "two-letter state code (AL, GA, etc.)",
    "zip_code": "5-digit zip",
    "county": "county name or null"
  },
  "financial_terms": {
    "purchase_price": 305000.00,
    "original_list_price": 309900.00,
    "down_payment": null,
    "financing_type": "fha",
    "earnest_money": 1000.00,
    "earnest_money_holder": "Graham Legal Firm",
    "seller_concessions": 7000.00,
    "home_warranty_amount": 799.00,
    "home_warranty_paid_by": "seller"
  },
  "parties": [
    {"name": "Full Name", "role": "buyer", "email": null, "phone": null, "company": null, "license_number": null},
    {"name": "Agent Name", "role": "buyer_agent", "email": null, "phone": null, "company": "Brokerage Name", "license_number": "12345"}
  ],
  "dates": {
    "contract_date": "2025-07-08",
    "closing_date": "2025-08-15",
    "inspection_deadline": "2025-07-23",
    "financing_deadline": "2025-07-11",
    "earnest_money_deadline": "2025-07-11",
    "appraisal_contingency_date": null,
    "offer_deadline": "2025-07-10"
  },
  "additional_provisions": {
    "provisions": ["Seller to pay 3% buyer's agent commission", "Seller to pay up to $7,000 in closing costs"],
    "contingencies": ["inspection", "financing", "appraisal"],
    "home_warranty": true,
    "wood_infestation_report": true,
    "lead_based_paint": false,
    "fha_va_agreement": true,
    "property_sale_contingency": false
  },
  "representation_side": "buyer",
  "contract_type": "LCAR Residential Real Estate Sales Contract",
  "confidence_scores": {
    "property_details": 0.95,
    "financial_terms": 0.90,
    "parties": 0.85,
    "dates": 0.92
  },
  "detected_features": ["fha_financing", "home_warranty", "seller_concessions", "wood_infestation"]
}

RULES:
- All dates must be ISO format (YYYY-MM-DD). Convert "7/8/2025" to "2025-07-08".
- financing_type must be one of: "conventional", "fha", "va", "cash", "usda", or null.
- Party roles must be one of: "buyer", "seller", "buyer_agent", "seller_agent", "lender", "closing_attorney", "title_company", "inspector".
- Include ALL buyers and sellers as separate party entries (e.g. if husband and wife are both buyers, list each).
- Include listing agent (role="seller_agent") and selling/buyer's agent (role="buyer_agent") with brokerage as company.
- For the closing agent/attorney/title company, use role="closing_attorney" or "title_company" as appropriate.
- representation_side: determine from the agency section — if the selling company represents the buyer, it's "buyer".
- seller_concessions: look for "closing costs and prepaids" caps, seller credits, etc.
- For detected_features, include tags like: fha_financing, va_financing, conventional_financing, cash_purchase, home_warranty, seller_concessions, wood_infestation, lead_paint, appraisal_contingency, inspection_contingency, financing_contingency, property_sale_contingency, counter_offer.
- If the purchase price differs from a counter/original price, set original_list_price to the counter/original.
- Set confidence_scores from 0.0 to 1.0 based on how clearly each section's data was found.
- If a field is not found in the document, use null (not empty string).

Return ONLY valid JSON. No markdown, no explanations, no code fences."""

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
                max_tokens=8192,
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

        # Handle legacy "dates" dict format — convert to ContractDates if needed
        if "dates" in parsed_json and isinstance(parsed_json["dates"], dict):
            dates_data = parsed_json["dates"]
            # Already matches ContractDates fields — Pydantic will handle it
            # But ensure old flat dict with arbitrary keys still works
            if not any(k in dates_data for k in ("contract_date", "closing_date", "inspection_deadline")):
                # Legacy format — try to map common keys
                mapped = {}
                for k, v in dates_data.items():
                    key_lower = k.lower().replace(" ", "_")
                    if "closing" in key_lower:
                        mapped["closing_date"] = v
                    elif "inspection" in key_lower:
                        mapped["inspection_deadline"] = v
                    elif "contract" in key_lower or "execution" in key_lower:
                        mapped["contract_date"] = v
                    elif "financing" in key_lower:
                        mapped["financing_deadline"] = v
                    elif "earnest" in key_lower:
                        mapped["earnest_money_deadline"] = v
                parsed_json["dates"] = mapped

        # Validate against schema
        validated = ContractExtractionSchema.model_validate(parsed_json)
        return validated.model_dump()
    except (json.JSONDecodeError, Exception) as e:
        logger.error("Failed to parse AI response as JSON: %s", str(e))
        logger.debug("Raw response: %s", raw_response[:500] if raw_response else "None")
        # Return a minimal valid structure on parse failure
        return {
            "property_details": {"address": "", "city": "", "state": "", "zip_code": "", "county": None},
            "financial_terms": {"purchase_price": 0, "down_payment": None, "financing_type": None},
            "parties": [],
            "dates": {},
            "additional_provisions": {"provisions": [], "contingencies": [], "home_warranty": False, "wood_infestation_report": False, "lead_based_paint": False, "fha_va_agreement": False, "property_sale_contingency": False},
            "confidence_scores": {},
            "detected_features": ["parse_error"],
        }

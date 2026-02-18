import asyncio
import base64
import json
import logging
from typing import Dict, List, Optional

import anthropic
import fitz  # PyMuPDF

from app.config import Settings

logger = logging.getLogger(__name__)
settings = Settings()

client = anthropic.AsyncAnthropic(api_key=settings.claude_api_key)

ADDENDUM_SYSTEM_PROMPT = """You are an expert real estate transaction coordinator AI that parses contract addenda and amendments.
You specialize in Alabama REALTORS and LCAR standard forms.

Given an addendum document (repair request, amendment, extension, etc.), extract all relevant information.

Return a JSON object with this exact structure:

{
  "addendum_type": "repair_request",
  "original_contract_date": "2025-07-08",
  "property_address": "37 Oakwood Drive, Phenix City, AL 36870",
  "buyers": ["Ke'Ana Hutchinson", "Mitchell Hutchinson"],
  "sellers": ["Benjamin T. Cupp", "Christine Cupp"],
  "signed_date": "2025-07-24",
  "items": [
    {
      "description": "Seller to repair or replace all siding with water damage and/or swelling. Caulk and seal all gaps, cracks, and openings.",
      "inspection_reference": "Page 6, Item 3",
      "responsible_party": "seller",
      "category": "exterior",
      "estimated_cost_low": 500,
      "estimated_cost_high": 2000
    }
  ],
  "total_estimated_cost_low": 2500,
  "total_estimated_cost_high": 8000,
  "confidence": 0.92
}

ADDENDUM TYPES:
- "repair_request": Buyer requesting repairs based on inspection findings
- "price_reduction": Agreement to reduce purchase price
- "closing_extension": Extending the closing date
- "contingency_removal": Removing a contingency
- "general_amendment": Any other modification to the purchase agreement

ITEM CATEGORIES:
- "exterior": Siding, paint, trim, gutters
- "roof": Roofing, shingles, flashing
- "hvac": Heating, air conditioning, ventilation
- "plumbing": Pipes, faucets, toilets, water heater
- "electrical": Wiring, outlets, panels, smoke detectors
- "structural": Foundation, framing, load-bearing
- "interior": Doors, windows, floors, walls, ceilings
- "safety": Smoke detectors, CO detectors, railings, fire doors
- "appliance": Kitchen appliances, washer/dryer
- "other": Anything else

COST ESTIMATION for repair items (use same ranges as home inspection):
- Caulking/sealing exterior: $200-500
- Siding repair (section): $500-2000
- Shingle repair: $200-500
- HVAC service: $150-300
- Deadbolt/latch repair: $75-200 each
- Smoke/CO detector install: $30-50 each
- Shower faucet repair: $100-250
- Toilet reanchoring: $100-200
- Ceiling stain investigation: $100-300

RULES:
- Extract EVERY repair/amendment item as a separate entry
- If the addendum references an inspection report (page/item numbers), include the reference
- responsible_party is usually "seller" for repair requests
- For price reductions, include a single item with the reduction amount
- For closing extensions, include the new date
- Sum total costs from all items
- All dates in ISO format (YYYY-MM-DD)

Return ONLY valid JSON. No markdown, no explanations, no code fences."""

MAX_RETRIES = 3
BASE_DELAY = 1.0


async def _call_claude_with_retry(messages: list, system: str, max_retries: int = MAX_RETRIES) -> str:
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
    images = []
    try:
        with fitz.open(file_path) as pdf_document:
            for page_num in range(min(len(pdf_document), 10)):
                page = pdf_document.load_page(page_num)
                pix = page.get_pixmap(dpi=200)
                img_bytes = pix.tobytes("png")
                images.append(base64.b64encode(img_bytes).decode("utf-8"))
    except Exception:
        logger.exception("Failed to extract images from PDF: %s", file_path)
    return images


async def parse_addendum(file_path: str) -> dict:
    """Parse a contract addendum/amendment PDF and return structured data."""
    if not file_path:
        raise ValueError("file_path is required")

    text = extract_text_from_pdf(file_path)

    if len(text.strip()) >= 100:
        logger.info("Parsing addendum via text (%d chars)", len(text))
        messages = [{"role": "user", "content": f"Parse this contract addendum/amendment and extract all information:\n\n{text}"}]
    else:
        logger.info("Text too short (%d chars) — using vision for addendum", len(text))
        images = extract_images_from_pdf(file_path)
        if not images:
            raise ValueError(f"Could not extract text or images from addendum PDF: {file_path}")
        content = [{"type": "text", "text": "Parse this contract addendum/amendment from the page images and extract all information:"}]
        for img_b64 in images:
            content.append({"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": img_b64}})
        messages = [{"role": "user", "content": content}]

    raw_response = await _call_claude_with_retry(messages, ADDENDUM_SYSTEM_PROMPT)

    try:
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        return json.loads(cleaned)
    except (json.JSONDecodeError, Exception) as e:
        logger.error("Failed to parse addendum AI response: %s", str(e))
        logger.debug("Raw response: %s", raw_response[:500] if raw_response else "None")
        return {
            "addendum_type": "unknown",
            "items": [],
            "confidence": 0.0,
        }

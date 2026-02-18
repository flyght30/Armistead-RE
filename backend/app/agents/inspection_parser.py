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

INSPECTION_SYSTEM_PROMPT = """You are an expert home inspection report analyzer for residential real estate transactions.
You parse home inspection reports and extract structured findings.

Given a home inspection report, extract ALL findings — both from the summary section AND from the detailed per-room sections.
Group and deduplicate findings. For each finding, determine severity and estimate repair costs.

Return a JSON object with this exact structure:

{
  "inspector": {
    "name": "Inspector name",
    "company": "Inspection company name",
    "license_number": null
  },
  "property_address": "37 Oakwood Dr, Phenix City, AL",
  "inspection_date": "2025-07-21",
  "executive_summary": "A 2-3 sentence overall assessment of the property condition, highlighting the most significant concerns.",
  "overall_risk_level": "medium",
  "items": [
    {
      "description": "Clear description of the issue found",
      "location": "Room or area (e.g., 'Exterior / Siding', 'Bathroom 2 / Shower')",
      "severity": "minor",
      "estimated_cost_low": 100,
      "estimated_cost_high": 300,
      "risk_assessment": "Brief explanation of why this matters (safety, structural, cosmetic, etc.)",
      "recommendation": "What should be done (Repair, Replace, Monitor, Service, etc.)",
      "report_reference": "Page 6, Item 3"
    }
  ],
  "total_estimated_cost_low": 2500,
  "total_estimated_cost_high": 8000,
  "confidence": 0.90
}

SEVERITY LEVELS:
- "critical": Immediate safety hazard, structural issue, or code violation that must be fixed (electrical hazards, foundation cracks, active leaks causing damage)
- "major": Significant issue requiring repair before/at closing, expensive fix (roof damage, HVAC replacement, plumbing issues)
- "moderate": Should be repaired but not urgent — affects function or could worsen (water damage, loose railings, missing detectors)
- "minor": Cosmetic or low-priority maintenance items (loose door handles, wobbling fan blades, cleaning needed)

COST ESTIMATION GUIDELINES:
- Caulking/sealing: $50-200
- Door latch/deadbolt repair: $75-200 per door
- Smoke/CO detector: $30-50 per unit (installed)
- Dryer vent cleaning: $100-200
- GFCI outlet installation: $100-200 per outlet
- Shingle repair (small area): $200-500
- Siding repair/replacement (section): $500-2000
- HVAC service/tune-up: $150-300
- HVAC condensation repair: $200-500
- Shower faucet repair: $100-250
- Toilet reanchoring: $100-200
- Ceiling fan balancing: $50-150
- Handrail repair: $100-300
- Grading/drainage: $500-2000
- Light fixture/bulb: $20-50

RULES:
- Merge duplicate/related findings into a single item (e.g., all door latch issues can be one item if in same area, or separate if different rooms)
- Keep report_reference to page/item from the original report so it can be cross-referenced with repair requests
- Sum up total_estimated_cost_low and total_estimated_cost_high from all items
- If the report has no findings, return an empty items array with "low" risk level
- Set overall_risk_level based on the worst findings: any critical = "high", multiple moderate = "medium", only minor = "low"

Return ONLY valid JSON. No markdown, no explanations, no code fences."""

MAX_RETRIES = 3
BASE_DELAY = 1.0


async def _call_claude_with_retry(messages: list, system: str, max_retries: int = MAX_RETRIES) -> str:
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
    try:
        with fitz.open(file_path) as pdf_document:
            text = ""
            for page_num in range(len(pdf_document)):
                page = pdf_document.load_page(page_num)
                text += f"\n--- Page {page_num + 1} ---\n"
                text += page.get_text("text")
            return text
    except Exception:
        logger.exception("Failed to extract text from PDF: %s", file_path)
        return ""


def extract_images_from_pdf(file_path: str, max_pages: int = 20) -> List[str]:
    images = []
    try:
        with fitz.open(file_path) as pdf_document:
            for page_num in range(min(len(pdf_document), max_pages)):
                page = pdf_document.load_page(page_num)
                pix = page.get_pixmap(dpi=150)
                img_bytes = pix.tobytes("png")
                images.append(base64.b64encode(img_bytes).decode("utf-8"))
    except Exception:
        logger.exception("Failed to extract images from PDF: %s", file_path)
    return images


async def parse_inspection_report(file_path: str) -> dict:
    """Parse a home inspection report PDF and return structured findings."""
    if not file_path:
        raise ValueError("file_path is required")

    text = extract_text_from_pdf(file_path)

    if len(text.strip()) >= 200:
        logger.info("Parsing inspection report via text (%d chars)", len(text))
        # For long inspection reports, we may need to truncate to fit context
        # Most inspection reports are 20-50 pages, ~500-2000 chars per page
        if len(text) > 80000:
            text = text[:80000] + "\n\n[TRUNCATED — remaining pages omitted]"
        messages = [{"role": "user", "content": f"Parse this home inspection report and extract all findings:\n\n{text}"}]
    else:
        logger.info("Text too short (%d chars) — using vision for inspection report", len(text))
        images = extract_images_from_pdf(file_path, max_pages=30)
        if not images:
            raise ValueError(f"Could not extract text or images from inspection PDF: {file_path}")
        content = [{"type": "text", "text": "Parse this home inspection report from the page images and extract all findings:"}]
        for img_b64 in images:
            content.append({"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": img_b64}})
        messages = [{"role": "user", "content": content}]

    raw_response = await _call_claude_with_retry(messages, INSPECTION_SYSTEM_PROMPT)

    try:
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        return json.loads(cleaned)
    except (json.JSONDecodeError, Exception) as e:
        logger.error("Failed to parse inspection AI response: %s", str(e))
        logger.debug("Raw response: %s", raw_response[:500] if raw_response else "None")
        return {
            "inspector": {},
            "property_address": "",
            "executive_summary": "Failed to parse inspection report.",
            "overall_risk_level": "medium",
            "items": [],
            "total_estimated_cost_low": 0,
            "total_estimated_cost_high": 0,
            "confidence": 0.0,
        }

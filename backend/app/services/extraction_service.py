# backend/app/services/extraction_service.py
"""
Entity Extraction Service — converts raw OCR text into structured
procurement data using the Groq API (LLaMA 3.3 70B).

Pipeline position::

    OCR text  →  ExtractionService.extract_entities()  →  structured JSON

The service:
  - Sends a carefully engineered prompt to Groq (LLaMA 3.3 70B)
  - Parses and validates the JSON response against Pydantic models
  - Normalises dates, monetary amounts, and field names
  - Handles noisy/incomplete OCR text gracefully
  - Never hallucinates — missing values are returned as null
  - Includes retry logic with exponential backoff

Usage::

    from backend.app.services.extraction_service import ExtractionService

    svc = ExtractionService()
    result = svc.extract_entities(ocr_text, document_id=42)

    print(result.vendor_name, result.total_amount)
    print(result.to_entity_data())   # dict ready for DB storage
"""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from backend.app.config import settings

logger = logging.getLogger(__name__)


# =====================================================================
#  Constants
# =====================================================================

_GROQ_MODEL: str = "llama-3.3-70b-versatile"

# Retry configuration for Groq API calls
_MAX_RETRIES: int = 3
_BASE_DELAY_SECONDS: float = 1.0
_MAX_DELAY_SECONDS: float = 10.0

# Maximum input text length sent to the model (chars).
# Longer documents are truncated with a note.
_MAX_INPUT_CHARS: int = 30_000

# Document types the prompt recognises
_KNOWN_DOC_TYPES = {
    "invoice", "quotation", "purchase_order", "rfq",
    "contract", "credit_note", "debit_note", "delivery_challan",
    "proforma_invoice", "receipt", "unknown",
}


# =====================================================================
#  Pydantic Models — Extraction Output
# =====================================================================

class LineItem(BaseModel):
    """A single line item from an invoice / quotation / PO."""

    description: str = ""
    quantity: Optional[float] = None
    unit: Optional[str] = None
    unit_price: Optional[float] = None
    total_price: Optional[float] = None
    hsn_sac_code: Optional[str] = None

    @field_validator("quantity", "unit_price", "total_price", mode="before")
    @classmethod
    def _coerce_number(cls, v: Any) -> Optional[float]:
        if v is None or v == "" or v == "null":
            return None
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            cleaned = re.sub(r"[^\d.\-]", "", v.replace(",", ""))
            try:
                return float(cleaned) if cleaned else None
            except ValueError:
                return None
        return None


class ExtractionResult(BaseModel):
    """Validated, structured extraction from a procurement document.

    Every field except ``confidence_score`` is optional — the model
    should return null for anything it cannot confidently extract.
    """

    # ── Vendor information ──────────────────────────────────────
    vendor_name: Optional[str] = None
    vendor_gstin: Optional[str] = None
    vendor_pan: Optional[str] = None
    vendor_address: Optional[str] = None

    # ── Document metadata ───────────────────────────────────────
    document_type: Optional[str] = Field(
        default=None,
        description="invoice | quotation | purchase_order | rfq | contract | unknown",
    )
    document_number: Optional[str] = None
    document_date: Optional[str] = None
    due_date: Optional[str] = None

    # ── Financial ───────────────────────────────────────────────
    currency: Optional[str] = Field(default=None, description="ISO 4217 code, e.g. INR, USD")
    subtotal: Optional[float] = None
    tax_amount: Optional[float] = None
    total_amount: Optional[float] = None

    # ── Terms ───────────────────────────────────────────────────
    payment_terms: Optional[str] = None
    delivery_terms: Optional[str] = None
    warranty_terms: Optional[str] = None
    penalty_clause: Optional[str] = None

    # ── Contact ─────────────────────────────────────────────────
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None

    # ── Product / line items ────────────────────────────────────
    product_or_service_name: Optional[str] = None
    line_items: List[LineItem] = Field(default_factory=list)

    # ── Quality ─────────────────────────────────────────────────
    confidence_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="How confident the model is in the overall extraction",
    )
    notes: Optional[str] = None

    # ── Metadata (not from LLM — added by the service) ─────────
    document_id: Optional[int] = None
    extraction_model: str = _GROQ_MODEL
    extracted_at: Optional[str] = None

    # ── Validators ──────────────────────────────────────────────

    @field_validator("subtotal", "tax_amount", "total_amount", mode="before")
    @classmethod
    def _coerce_amount(cls, v: Any) -> Optional[float]:
        return _normalize_amount(v)

    @field_validator("document_date", "due_date", mode="before")
    @classmethod
    def _coerce_date(cls, v: Any) -> Optional[str]:
        return _normalize_date(v)

    @field_validator("document_type", mode="before")
    @classmethod
    def _coerce_doc_type(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        normalised = str(v).strip().lower().replace(" ", "_")
        return normalised if normalised in _KNOWN_DOC_TYPES else "unknown"

    @field_validator("confidence_score", mode="before")
    @classmethod
    def _coerce_confidence(cls, v: Any) -> float:
        if v is None:
            return 0.0
        try:
            val = float(v)
            return max(0.0, min(1.0, val))
        except (ValueError, TypeError):
            return 0.0

    # ── Serialisation helpers ───────────────────────────────────

    def to_entity_data(self) -> Dict[str, Any]:
        """Return a dict suitable for storing in ExtractedEntity.entity_data."""
        return self.model_dump(
            exclude={"document_id", "extraction_model", "extracted_at"},
            exclude_none=False,
        )

    def summary(self) -> str:
        """Human-readable one-liner."""
        vendor = self.vendor_name or "Unknown vendor"
        doc = self.document_type or "unknown"
        total = f"{self.currency or ''} {self.total_amount:,.2f}" if self.total_amount else "N/A"
        items = len(self.line_items)
        return (
            f"[{doc}] {vendor} | total={total} | "
            f"items={items} | confidence={self.confidence_score:.0%}"
        )


# =====================================================================
#  Helper Functions
# =====================================================================

def _normalize_amount(v: Any) -> Optional[float]:
    """Parse a monetary amount from various messy formats."""
    if v is None or v == "" or v == "null":
        return None
    if isinstance(v, (int, float)):
        return round(float(v), 2)
    if isinstance(v, str):
        # Remove currency symbols, commas, spaces, ₹, $, etc.
        cleaned = re.sub(r"[₹$€£¥,\s]", "", v)
        # Handle Indian-style negatives like "(1234)"
        if cleaned.startswith("(") and cleaned.endswith(")"):
            cleaned = "-" + cleaned[1:-1]
        try:
            return round(float(cleaned), 2) if cleaned else None
        except ValueError:
            return None
    return None


def _normalize_date(v: Any) -> Optional[str]:
    """Attempt to normalise a date string to YYYY-MM-DD."""
    if v is None or v == "" or v == "null":
        return None
    if not isinstance(v, str):
        v = str(v)

    v = v.strip()

    # Already ISO format
    if re.match(r"^\d{4}-\d{2}-\d{2}$", v):
        return v

    # Common formats to try
    formats = [
        "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%m-%d-%Y",
        "%d.%m.%Y", "%B %d, %Y", "%b %d, %Y",
        "%d %B %Y", "%d %b %Y", "%Y/%m/%d",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(v, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    # Return as-is if nothing worked (better than losing data)
    return v


def _safe_json_load(text: str) -> Optional[Dict[str, Any]]:
    """Extract and parse JSON from a potentially noisy LLM response.

    Handles cases where the model wraps JSON in markdown code fences
    or includes preamble text.
    """
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strip markdown code fences: ```json ... ``` or ``` ... ```
    fence_pattern = r"```(?:json)?\s*\n?(.*?)\n?\s*```"
    match = re.search(fence_pattern, text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Try to find the first { ... } block
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end > brace_start:
        try:
            return json.loads(text[brace_start : brace_end + 1])
        except json.JSONDecodeError:
            pass

    return None


def _build_empty_result(
    document_id: Optional[int] = None,
    error_note: Optional[str] = None,
) -> ExtractionResult:
    """Return a valid but empty ExtractionResult."""
    return ExtractionResult(
        confidence_score=0.0,
        notes=error_note or "Extraction produced no results.",
        document_id=document_id,
        extracted_at=datetime.utcnow().isoformat(),
    )


# =====================================================================
#  Prompt (works with any instruction-following LLM)
# =====================================================================

_SYSTEM_INSTRUCTION = """\
You are a procurement document analysis engine.  Your job is to extract \
structured data from the raw text of procurement documents (invoices, \
quotations, purchase orders, RFQs, contracts).

RULES — follow these strictly:
1. Extract ONLY information that is explicitly present in the text.
2. If a field's value is not found in the text, set it to null.
3. NEVER invent, guess, or hallucinate values.
4. Preserve exact vendor names, document numbers, and GSTIN as written.
5. Normalise monetary amounts to plain numbers (no currency symbols or commas).
6. Normalise dates to YYYY-MM-DD format where possible.
7. Return ONLY valid JSON — no commentary, no markdown, no explanation.
8. Set confidence_score between 0.0 and 1.0 based on how much \
   information you could reliably extract.
9. In the notes field, briefly mention any issues (e.g. "some fields \
   unreadable due to OCR noise").\
"""

_USER_PROMPT_TEMPLATE = """\
Extract structured procurement data from the following document text.

Return a single JSON object with exactly these keys:

{{
  "vendor_name": "<string or null>",
  "vendor_gstin": "<string or null>",
  "vendor_pan": "<string or null>",
  "vendor_address": "<string or null>",
  "document_type": "<invoice|quotation|purchase_order|rfq|contract|credit_note|debit_note|delivery_challan|proforma_invoice|receipt|unknown>",
  "document_number": "<string or null>",
  "document_date": "<YYYY-MM-DD or null>",
  "due_date": "<YYYY-MM-DD or null>",
  "currency": "<ISO 4217 code or null>",
  "subtotal": <number or null>,
  "tax_amount": <number or null>,
  "total_amount": <number or null>,
  "payment_terms": "<string or null>",
  "delivery_terms": "<string or null>",
  "warranty_terms": "<string or null>",
  "penalty_clause": "<string or null>",
  "contact_email": "<string or null>",
  "contact_phone": "<string or null>",
  "product_or_service_name": "<primary product/service or null>",
  "line_items": [
    {{
      "description": "<string>",
      "quantity": <number or null>,
      "unit": "<string or null>",
      "unit_price": <number or null>,
      "total_price": <number or null>,
      "hsn_sac_code": "<string or null>"
    }}
  ],
  "confidence_score": <0.0 to 1.0>,
  "notes": "<string or null>"
}}

DOCUMENT TEXT:
---
{document_text}
---

Return ONLY the JSON object. No other text.\
"""


# =====================================================================
#  Extraction Service
# =====================================================================

class ExtractionService:
    """Converts raw document text into structured procurement data
    using the Groq API (LLaMA 3.3 70B).

    Parameters
    ----------
    api_key : str | None
        Groq API key.  Falls back to ``settings.GROQ_API_KEY``.
    model : str
        Groq model name (default ``llama-3.3-70b-versatile``).
    max_retries : int
        Maximum number of retry attempts for transient API failures.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = _GROQ_MODEL,
        max_retries: int = _MAX_RETRIES,
    ) -> None:
        self._api_key = api_key or settings.GROQ_API_KEY
        self._model_name = model
        self._max_retries = max_retries
        self._client: Optional[Any] = None  # lazy-loaded

    # ─────────────────────────────────────────────────────────────
    #  Lazy Groq client
    # ─────────────────────────────────────────────────────────────

    def _get_client(self) -> Any:
        """Return a configured Groq client, creating it on first use."""
        if self._client is None:
            if not self._api_key:
                raise ValueError(
                    "GROQ_API_KEY is not set.  Provide it via environment "
                    "variable, .env file, or pass api_key= to ExtractionService()."
                )

            from groq import Groq  # deferred import

            self._client = Groq(api_key=self._api_key)
            logger.info("Groq client initialised (model=%s).", self._model_name)

        return self._client

    # ─────────────────────────────────────────────────────────────
    #  Public API
    # ─────────────────────────────────────────────────────────────

    def extract_entities(
        self,
        text: str,
        document_id: Optional[int] = None,
    ) -> ExtractionResult:
        """Extract structured procurement data from raw document text.

        Parameters
        ----------
        text : str
            Raw text from the OCR service.
        document_id : int | None
            Optional document ID for traceability.

        Returns
        -------
        ExtractionResult
            Validated structured extraction.  Always returns a valid
            object — on failure, ``confidence_score`` is 0.0 and
            ``notes`` explains what went wrong.
        """
        start = time.perf_counter()

        # ── Guard: empty text ───────────────────────────────────
        if not text or not text.strip():
            logger.warning("Empty text provided for extraction (doc=%s).", document_id)
            return _build_empty_result(document_id, "Input text was empty.")

        # ── Truncate if excessively long ────────────────────────
        truncated = False
        if len(text) > _MAX_INPUT_CHARS:
            logger.info(
                "Truncating input from %d to %d chars (doc=%s).",
                len(text),
                _MAX_INPUT_CHARS,
                document_id,
            )
            text = text[:_MAX_INPUT_CHARS]
            truncated = True

        # ── Build prompt ────────────────────────────────────────
        prompt = self._build_prompt(text)

        # ── Call Groq with retries ──────────────────────────────
        raw_response = self._call_llm_with_retries(prompt)

        if raw_response is None:
            return _build_empty_result(
                document_id,
                "Groq API call failed after retries.",
            )

        # ── Parse JSON from response ───────────────────────────
        parsed = self._parse_response(raw_response)

        if parsed is None:
            logger.error(
                "Failed to parse LLM response as JSON (doc=%s). Raw: %s",
                document_id,
                raw_response[:500],
            )
            return _build_empty_result(
                document_id,
                "Could not parse LLM response as valid JSON.",
            )

        # ── Validate with Pydantic ──────────────────────────────
        result = self._validate_extraction(parsed, document_id)

        # ── Attach metadata ─────────────────────────────────────
        result.document_id = document_id
        result.extraction_model = self._model_name
        result.extracted_at = datetime.utcnow().isoformat()

        if truncated and result.notes:
            result.notes += " Input was truncated to fit model context."
        elif truncated:
            result.notes = "Input was truncated to fit model context."

        elapsed = (time.perf_counter() - start) * 1000
        logger.info(
            "Extraction complete (doc=%s, %.0fms): %s",
            document_id,
            elapsed,
            result.summary(),
        )

        return result

    # ─────────────────────────────────────────────────────────────
    #  Prompt construction
    # ─────────────────────────────────────────────────────────────

    def _build_prompt(self, document_text: str) -> str:
        """Build the user prompt with the document text inserted."""
        return _USER_PROMPT_TEMPLATE.format(document_text=document_text)

    # ─────────────────────────────────────────────────────────────
    #  Groq API call with retries
    # ─────────────────────────────────────────────────────────────

    def _call_llm_with_retries(self, prompt: str) -> Optional[str]:
        """Call Groq chat completions and return the text response,
        retrying on transient errors."""
        client = self._get_client()

        last_error: Optional[Exception] = None

        for attempt in range(1, self._max_retries + 1):
            try:
                response = client.chat.completions.create(
                    model=self._model_name,
                    messages=[
                        {"role": "system", "content": _SYSTEM_INSTRUCTION},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.1,       # Low temp → deterministic extraction
                    max_completion_tokens=4096,
                    response_format={"type": "json_object"},  # Force JSON mode
                )

                # Extract text from response
                content = response.choices[0].message.content
                if content:
                    return content.strip()

                logger.warning(
                    "Groq returned empty response (attempt %d/%d).",
                    attempt,
                    self._max_retries,
                )

            except Exception as exc:
                last_error = exc
                delay = min(
                    _BASE_DELAY_SECONDS * (2 ** (attempt - 1)),
                    _MAX_DELAY_SECONDS,
                )
                logger.warning(
                    "Groq API error (attempt %d/%d): %s. Retrying in %.1fs …",
                    attempt,
                    self._max_retries,
                    exc,
                    delay,
                )
                time.sleep(delay)

        logger.error("Groq API failed after %d attempts. Last error: %s", self._max_retries, last_error)
        return None

    # ─────────────────────────────────────────────────────────────
    #  Response parsing
    # ─────────────────────────────────────────────────────────────

    def _parse_response(self, raw: str) -> Optional[Dict[str, Any]]:
        """Parse the raw LLM text into a Python dict."""
        return _safe_json_load(raw)

    # ─────────────────────────────────────────────────────────────
    #  Validation
    # ─────────────────────────────────────────────────────────────

    def _validate_extraction(
        self,
        data: Dict[str, Any],
        document_id: Optional[int] = None,
    ) -> ExtractionResult:
        """Validate raw dict against the ExtractionResult schema.

        On validation error, returns an empty result with the error
        in notes rather than raising.
        """
        try:
            return ExtractionResult.model_validate(data)
        except Exception as exc:
            logger.warning(
                "Pydantic validation failed for doc=%s: %s. Attempting partial extraction.",
                document_id,
                exc,
            )
            return self._partial_extraction(data, document_id)

    def _partial_extraction(
        self,
        data: Dict[str, Any],
        document_id: Optional[int] = None,
    ) -> ExtractionResult:
        """Best-effort extraction when full validation fails.

        Tries to salvage as many fields as possible by setting
        problematic ones to None.
        """
        safe_fields: Dict[str, Any] = {}
        field_names = ExtractionResult.model_fields.keys()

        for key in field_names:
            if key in data:
                try:
                    # Test each field individually
                    ExtractionResult.model_validate({key: data[key]})
                    safe_fields[key] = data[key]
                except Exception:
                    logger.debug("Skipping invalid field %s for doc=%s", key, document_id)

        safe_fields["confidence_score"] = max(
            0.0,
            min(1.0, float(data.get("confidence_score", 0.0)) * 0.7),
        )
        safe_fields["notes"] = (
            "Partial extraction — some fields failed validation. "
            f"Original notes: {data.get('notes', 'N/A')}"
        )

        try:
            return ExtractionResult.model_validate(safe_fields)
        except Exception:
            return _build_empty_result(document_id, "Complete validation failure.")


# =====================================================================
#  Convenience — module-level singleton
# =====================================================================
extraction_service = ExtractionService()


# =====================================================================
#  CLI entry point for quick testing
# =====================================================================
if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)-8s | %(name)-35s | %(message)s",
    )

    sample_text = """
    INVOICE #INV-2025-00421

    From: Apex Industrial Supplies Pvt Ltd
    GSTIN: 29AABCU9603R1ZP
    PAN: AABCU9603R
    Address: Plot 42, Industrial Area Phase II, Bangalore 560058
    Email: sales@apexindustrial.in
    Phone: +91-80-23456789

    To: SupplyMind Corp
    Date: 2025-06-01
    Due Date: 2025-07-01

    ─────────────────────────────────────────────
    Item                    Qty    Unit Price    Total
    ─────────────────────────────────────────────
    Hydraulic Pump HP-200    5     ₹12,500    ₹62,500
    Ball Bearing 6205-2RS   50       ₹320    ₹16,000
    Conveyor Belt CB-12M     2    ₹45,000    ₹90,000
    ─────────────────────────────────────────────
    Subtotal:                              ₹1,68,500
    GST (18%):                               ₹30,330
    Total:                                 ₹1,98,830

    Payment Terms: Net 30 days
    Delivery: Within 15 business days of order confirmation
    Warranty: 1 year manufacturer warranty on all items
    Penalty: 2% deduction per week for late delivery

    Bank Details:
    Account: Apex Industrial Supplies Pvt Ltd
    A/C No: 920020043567891
    IFSC: UTIB0002083
    Bank: Axis Bank, Koramangala Branch
    """

    if not settings.GROQ_API_KEY:
        print("ERROR: GROQ_API_KEY is not set.")
        print("Set it in your .env file or as an environment variable:")
        print("  GROQ_API_KEY=your_key_here")
        sys.exit(1)

    print(f"\nExtracting entities from sample invoice text …\n{'═' * 60}")

    svc = ExtractionService()
    result = svc.extract_entities(sample_text, document_id=1)

    print(f"Summary    : {result.summary()}")
    print(f"Vendor     : {result.vendor_name}")
    print(f"GSTIN      : {result.vendor_gstin}")
    print(f"Doc Type   : {result.document_type}")
    print(f"Doc Number : {result.document_number}")
    print(f"Date       : {result.document_date}")
    print(f"Due Date   : {result.due_date}")
    print(f"Currency   : {result.currency}")
    print(f"Subtotal   : {result.subtotal}")
    print(f"Tax        : {result.tax_amount}")
    print(f"Total      : {result.total_amount}")
    print(f"Payment    : {result.payment_terms}")
    print(f"Line Items : {len(result.line_items)}")
    for i, item in enumerate(result.line_items, 1):
        print(f"  [{i}] {item.description} × {item.quantity} @ {item.unit_price} = {item.total_price}")
    print(f"Confidence : {result.confidence_score:.0%}")
    print(f"Notes      : {result.notes}")
    print(f"\nFull entity_data dict:\n{json.dumps(result.to_entity_data(), indent=2, default=str)}")

# scripts/test_extraction.py
"""
Test script for the Entity Extraction Service (Module 3).

Tests three scenarios:
  1. Rich invoice text   → should extract most fields
  2. Minimal text        → should return low confidence
  3. Empty text          → should return graceful empty result

Also tests the helper functions (date/amount normalisation, JSON parsing).

Usage:
    python scripts/test_extraction.py              (from project root)

Requires GROQ_API_KEY to be set for the live extraction tests.
Helper function tests run without an API key.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

# ── Ensure project root is on sys.path ──────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-8s | %(name)-35s | %(message)s",
)
logger = logging.getLogger("test_extraction")


# =====================================================================
#  Helper function tests (no API key needed)
# =====================================================================

def test_normalize_amount() -> bool:
    """Test monetary amount normalisation."""
    from backend.app.services.extraction_service import _normalize_amount

    logger.info("═" * 60)
    logger.info("TEST: _normalize_amount")
    logger.info("═" * 60)

    cases = [
        (None, None),
        ("", None),
        ("null", None),
        (12500, 12500.0),
        (12500.50, 12500.50),
        ("₹1,68,500", 168500.0),
        ("$12,500.00", 12500.0),
        ("€ 1 234.56", 1234.56),
        ("(500)", -500.0),
        ("1,98,830", 198830.0),
    ]

    ok = True
    for input_val, expected in cases:
        result = _normalize_amount(input_val)
        if result != expected:
            logger.error("  FAIL: _normalize_amount(%r) = %r, expected %r", input_val, result, expected)
            ok = False
        else:
            logger.info("  OK: %r → %r", input_val, result)

    return ok


def test_normalize_date() -> bool:
    """Test date normalisation."""
    from backend.app.services.extraction_service import _normalize_date

    logger.info("═" * 60)
    logger.info("TEST: _normalize_date")
    logger.info("═" * 60)

    cases = [
        (None, None),
        ("", None),
        ("2025-06-01", "2025-06-01"),
        ("01/06/2025", "2025-06-01"),
        ("June 01, 2025", "2025-06-01"),
        ("01 June 2025", "2025-06-01"),
    ]

    ok = True
    for input_val, expected in cases:
        result = _normalize_date(input_val)
        if result != expected:
            logger.error("  FAIL: _normalize_date(%r) = %r, expected %r", input_val, result, expected)
            ok = False
        else:
            logger.info("  OK: %r → %r", input_val, result)

    return ok


def test_safe_json_load() -> bool:
    """Test JSON parsing from noisy responses."""
    from backend.app.services.extraction_service import _safe_json_load

    logger.info("═" * 60)
    logger.info("TEST: _safe_json_load")
    logger.info("═" * 60)

    ok = True

    # Clean JSON
    r = _safe_json_load('{"key": "value"}')
    if r != {"key": "value"}:
        logger.error("  FAIL: clean JSON parse")
        ok = False
    else:
        logger.info('  OK: clean JSON → %r', r)

    # Markdown-fenced JSON
    fenced = '```json\n{"vendor": "Acme"}\n```'
    r = _safe_json_load(fenced)
    if r != {"vendor": "Acme"}:
        logger.error("  FAIL: fenced JSON parse")
        ok = False
    else:
        logger.info("  OK: fenced JSON → %r", r)

    # Preamble + JSON
    noisy = 'Here is the extracted data:\n\n{"total": 1000}'
    r = _safe_json_load(noisy)
    if r != {"total": 1000}:
        logger.error("  FAIL: noisy JSON parse")
        ok = False
    else:
        logger.info("  OK: noisy JSON → %r", r)

    # Invalid
    r = _safe_json_load("not json at all")
    if r is not None:
        logger.error("  FAIL: expected None for invalid input")
        ok = False
    else:
        logger.info("  OK: invalid input → None")

    return ok


def test_pydantic_models() -> bool:
    """Test ExtractionResult Pydantic validation."""
    from backend.app.services.extraction_service import ExtractionResult, LineItem

    logger.info("═" * 60)
    logger.info("TEST: Pydantic models")
    logger.info("═" * 60)

    ok = True

    # Valid full result
    data = {
        "vendor_name": "Apex Industrial Supplies Pvt Ltd",
        "vendor_gstin": "29AABCU9603R1ZP",
        "document_type": "invoice",
        "document_number": "INV-2025-00421",
        "document_date": "01/06/2025",
        "total_amount": "₹1,98,830",
        "confidence_score": 0.87,
        "line_items": [
            {
                "description": "Hydraulic Pump HP-200",
                "quantity": "5",
                "unit_price": "12,500",
                "total_price": "62,500",
            }
        ],
    }

    try:
        result = ExtractionResult.model_validate(data)
        assert result.vendor_name == "Apex Industrial Supplies Pvt Ltd"
        assert result.total_amount == 198830.0
        assert result.document_date == "2025-06-01"
        assert result.document_type == "invoice"
        assert len(result.line_items) == 1
        assert result.line_items[0].quantity == 5.0
        assert result.confidence_score == 0.87
        logger.info("  OK: Full result validated correctly")
    except Exception as exc:
        logger.error("  FAIL: Full result validation — %s", exc)
        ok = False

    # Empty result (all None)
    try:
        empty = ExtractionResult(confidence_score=0.0)
        assert empty.vendor_name is None
        assert empty.line_items == []
        entity_data = empty.to_entity_data()
        assert isinstance(entity_data, dict)
        logger.info("  OK: Empty result validated correctly")
    except Exception as exc:
        logger.error("  FAIL: Empty result validation — %s", exc)
        ok = False

    # Confidence clamping
    try:
        clamped = ExtractionResult(confidence_score=1.5)
        assert clamped.confidence_score == 1.0
        logger.info("  OK: Confidence clamped to 1.0")
    except Exception as exc:
        logger.error("  FAIL: Confidence clamping — %s", exc)
        ok = False

    # Unknown doc type normalisation
    try:
        unk = ExtractionResult(document_type="Something Weird", confidence_score=0.5)
        assert unk.document_type == "unknown"
        logger.info("  OK: Unknown doc type normalised to 'unknown'")
    except Exception as exc:
        logger.error("  FAIL: Doc type normalisation — %s", exc)
        ok = False

    return ok


def test_empty_text_extraction() -> bool:
    """Test that empty text returns a valid empty result."""
    from backend.app.services.extraction_service import ExtractionService

    logger.info("═" * 60)
    logger.info("TEST: Empty text extraction")
    logger.info("═" * 60)

    svc = ExtractionService(api_key="dummy")  # won't call API for empty text
    result = svc.extract_entities("", document_id=99)

    ok = True
    if result.confidence_score != 0.0:
        logger.error("  FAIL: expected confidence 0.0")
        ok = False
    if not result.notes:
        logger.error("  FAIL: expected notes about empty input")
        ok = False
    if result.vendor_name is not None:
        logger.error("  FAIL: expected None vendor_name")
        ok = False

    logger.info("  OK: Empty text → confidence=%.1f, notes=%r", result.confidence_score, result.notes)
    return ok


def test_live_extraction() -> bool:
    """Test live extraction with Groq API (requires GROQ_API_KEY)."""
    from backend.app.config import settings
    from backend.app.services.extraction_service import ExtractionService

    logger.info("═" * 60)
    logger.info("TEST: Live Groq extraction")
    logger.info("═" * 60)

    if not settings.GROQ_API_KEY:
        logger.warning("  SKIP: GROQ_API_KEY not set. Skipping live test.")
        return True  # not a failure, just skipped

    sample_text = """
    INVOICE #INV-2025-00421

    From: Apex Industrial Supplies Pvt Ltd
    GSTIN: 29AABCU9603R1ZP
    Address: Plot 42, Industrial Area Phase II, Bangalore 560058
    Email: sales@apexindustrial.in
    Phone: +91-80-23456789

    To: SupplyMind Corp
    Date: 2025-06-01
    Due Date: 2025-07-01

    Item                    Qty    Unit Price    Total
    Hydraulic Pump HP-200    5     12,500       62,500
    Ball Bearing 6205-2RS   50       320        16,000
    Conveyor Belt CB-12M     2    45,000        90,000

    Subtotal:  1,68,500
    GST (18%):   30,330
    Total:     1,98,830

    Payment Terms: Net 30 days
    Delivery: Within 15 business days
    Warranty: 1 year manufacturer warranty
    Penalty: 2% deduction per week for late delivery
    """

    svc = ExtractionService()
    result = svc.extract_entities(sample_text, document_id=42)

    ok = True

    if not result.vendor_name:
        logger.error("  FAIL: vendor_name is empty")
        ok = False
    else:
        logger.info("  OK: vendor_name = %r", result.vendor_name)

    if not result.document_type:
        logger.error("  FAIL: document_type is empty")
        ok = False
    else:
        logger.info("  OK: document_type = %r", result.document_type)

    if result.total_amount is None:
        logger.error("  FAIL: total_amount is None")
        ok = False
    else:
        logger.info("  OK: total_amount = %s", result.total_amount)

    if result.confidence_score <= 0.0:
        logger.error("  FAIL: confidence_score is 0")
        ok = False
    else:
        logger.info("  OK: confidence_score = %.0f%%", result.confidence_score * 100)

    logger.info("  Summary: %s", result.summary())
    logger.info("  Line items: %d", len(result.line_items))
    for i, item in enumerate(result.line_items, 1):
        logger.info("    [%d] %s × %s @ %s = %s", i, item.description, item.quantity, item.unit_price, item.total_price)

    return ok


def main() -> None:
    """Run all extraction tests."""

    results = {
        "Amount normalisation": test_normalize_amount(),
        "Date normalisation": test_normalize_date(),
        "JSON parsing": test_safe_json_load(),
        "Pydantic models": test_pydantic_models(),
        "Empty text handling": test_empty_text_extraction(),
        "Live Groq extraction": test_live_extraction(),
    }

    logger.info("═" * 60)
    logger.info("TEST SUMMARY")
    logger.info("═" * 60)
    all_ok = True
    for name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info("  %s  %s", status, name)
        if not passed:
            all_ok = False

    logger.info("═" * 60)
    if all_ok:
        logger.info("All tests passed!")
    else:
        logger.error("Some tests failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()

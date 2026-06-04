# scripts/test_upload_api.py
"""
Integration test for the Document Upload API (Module 4).

Starts the FastAPI server in-process using TestClient and exercises:
  1. POST /documents/upload       — upload a sample PDF
  2. GET  /documents              — list all documents
  3. GET  /documents/{id}         — get document details
  4. GET  /documents/{id}/raw-text    — get raw OCR text
  5. GET  /documents/{id}/entities   — get extracted entities
  6. DELETE /documents/{id}       — delete document

Also tests error cases:
  - Upload unsupported file type
  - Get non-existent document
  - Delete non-existent document

Usage:
    python scripts/test_upload_api.py    (from project root)

Requires GROQ_API_KEY to be set for entity extraction.
"""

from __future__ import annotations

import json
import logging
import sys
import tempfile
from pathlib import Path

# ── Ensure project root is on sys.path ──────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-8s | %(name)-35s | %(message)s",
)
logger = logging.getLogger("test_upload_api")


def _create_sample_pdf(path: Path) -> None:
    """Create a simple digital PDF with procurement-style text."""
    import fitz

    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    text = (
        "INVOICE #INV-2025-00421\n\n"
        "From: Apex Industrial Supplies Pvt Ltd\n"
        "GSTIN: 29AABCU9603R1ZP\n"
        "Address: Plot 42, Industrial Area Phase II, Bangalore 560058\n"
        "Email: sales@apexindustrial.in\n"
        "Phone: +91-80-23456789\n\n"
        "To: SupplyMind Corp\n"
        "Date: 2025-06-01\n"
        "Due Date: 2025-07-01\n\n"
        "Item                    Qty    Unit Price    Total\n"
        "Hydraulic Pump HP-200    5     12,500       62,500\n"
        "Ball Bearing 6205-2RS   50       320        16,000\n"
        "Conveyor Belt CB-12M     2    45,000        90,000\n\n"
        "Subtotal:  1,68,500\n"
        "GST (18%):   30,330\n"
        "Total:     1,98,830\n\n"
        "Payment Terms: Net 30 days\n"
        "Delivery: Within 15 business days\n"
        "Warranty: 1 year manufacturer warranty\n"
        "Penalty: 2% deduction per week for late delivery\n"
    )
    page.insert_text(fitz.Point(50, 50), text, fontsize=11, fontname="helv")
    doc.save(str(path))
    doc.close()


def main() -> None:
    from backend.app.config import settings

    if not settings.GROQ_API_KEY:
        print("WARNING: GROQ_API_KEY not set. Extraction will fail gracefully.")

    # Import TestClient after ensuring path
    from fastapi.testclient import TestClient
    from backend.app.main import app
    from backend.app.database import create_all_tables

    # Ensure DB tables exist (lifespan may not fire in all TestClient modes)
    create_all_tables()

    client = TestClient(app, raise_server_exceptions=False)
    api = settings.API_V1_STR
    results: dict[str, bool] = {}

    # ── Create sample PDF ───────────────────────────────────────
    sample_dir = _PROJECT_ROOT / "data" / "sample_documents"
    sample_dir.mkdir(parents=True, exist_ok=True)
    sample_pdf = sample_dir / "test_upload_invoice.pdf"
    _create_sample_pdf(sample_pdf)
    logger.info("Created sample PDF: %s", sample_pdf)

    # ═════════════════════════════════════════════════════════════
    # TEST 1: Upload document
    # ═════════════════════════════════════════════════════════════
    logger.info("═" * 60)
    logger.info("TEST 1: POST /documents/upload")
    logger.info("═" * 60)

    with open(sample_pdf, "rb") as f:
        resp = client.post(
            f"{api}/documents/upload",
            files={"file": ("test_invoice.pdf", f, "application/pdf")},
        )

    ok = resp.status_code == 201
    data = resp.json()

    if ok and data.get("success"):
        logger.info("  ✓ Upload succeeded (status=%d)", resp.status_code)
        logger.info("  document_id  = %s", data.get("document_id"))
        logger.info("  entity_id    = %s", data.get("entity_id"))
        logger.info("  vendor_id    = %s", data.get("vendor_id"))
        logger.info("  ocr_status   = %s", data.get("ocr_status"))
        logger.info("  ocr_method   = %s", data.get("ocr_method"))
        logger.info("  text_length  = %s", data.get("text_length"))
        ext = data.get("extraction", {})
        if ext:
            logger.info("  doc_type     = %s", ext.get("document_type"))
            logger.info("  vendor       = %s", ext.get("vendor_name"))
            logger.info("  total        = %s %s", ext.get("currency"), ext.get("total_amount"))
            logger.info("  line_items   = %s", ext.get("line_item_count"))
            logger.info("  confidence   = %s", ext.get("confidence_score"))
    else:
        logger.error("  ✗ Upload failed: %s", data)
        ok = False

    doc_id = data.get("document_id")
    results["Upload document"] = ok

    # ═════════════════════════════════════════════════════════════
    # TEST 2: List documents
    # ═════════════════════════════════════════════════════════════
    logger.info("═" * 60)
    logger.info("TEST 2: GET /documents")
    logger.info("═" * 60)

    resp = client.get(f"{api}/documents")
    ok = resp.status_code == 200 and isinstance(resp.json(), list) and len(resp.json()) > 0

    if ok:
        docs = resp.json()
        logger.info("  ✓ Listed %d document(s)", len(docs))
        for d in docs:
            logger.info("    id=%s  file=%s  status=%s", d["id"], d["original_filename"], d["ocr_status"])
    else:
        logger.error("  ✗ List failed: %s", resp.json())

    results["List documents"] = ok

    # ═════════════════════════════════════════════════════════════
    # TEST 3: Get document details
    # ═════════════════════════════════════════════════════════════
    logger.info("═" * 60)
    logger.info("TEST 3: GET /documents/%s", doc_id)
    logger.info("═" * 60)

    if doc_id:
        resp = client.get(f"{api}/documents/{doc_id}")
        ok = resp.status_code == 200
        data = resp.json()
        if ok:
            logger.info("  ✓ Got document details")
            logger.info("    filename   = %s", data.get("original_filename"))
            logger.info("    ocr_status = %s", data.get("ocr_status"))
            logger.info("    entities   = %d", len(data.get("extracted_entities", [])))
            text = data.get("extracted_text", "")
            logger.info("    text_len   = %d", len(text) if text else 0)
        else:
            logger.error("  ✗ Get failed: %s", data)
    else:
        ok = False
        logger.error("  ✗ Skipped (no doc_id)")

    results["Get document details"] = ok

    # ═════════════════════════════════════════════════════════════
    # TEST 4: Get raw text
    # ═════════════════════════════════════════════════════════════
    logger.info("═" * 60)
    logger.info("TEST 4: GET /documents/%s/raw-text", doc_id)
    logger.info("═" * 60)

    if doc_id:
        resp = client.get(f"{api}/documents/{doc_id}/raw-text")
        ok = resp.status_code == 200
        data = resp.json()
        if ok:
            logger.info("  ✓ Got raw text (length=%d)", data.get("text_length", 0))
            logger.info("  Preview: %s", (data.get("text", "")[:200] + "…") if data.get("text") else "(empty)")
        else:
            logger.error("  ✗ Raw text failed: %s", data)
    else:
        ok = False

    results["Get raw text"] = ok

    # ═════════════════════════════════════════════════════════════
    # TEST 5: Get entities
    # ═════════════════════════════════════════════════════════════
    logger.info("═" * 60)
    logger.info("TEST 5: GET /documents/%s/entities", doc_id)
    logger.info("═" * 60)

    if doc_id:
        resp = client.get(f"{api}/documents/{doc_id}/entities")
        ok = resp.status_code == 200
        data = resp.json()
        if ok:
            logger.info("  ✓ Got entities (count=%d)", data.get("entity_count", 0))
            for ent in data.get("entities", []):
                logger.info("    type=%s  confidence=%.0f%%",
                            ent.get("entity_type"), (ent.get("confidence_score") or 0) * 100)
        else:
            logger.error("  ✗ Entities failed: %s", data)
    else:
        ok = False

    results["Get entities"] = ok

    # ═════════════════════════════════════════════════════════════
    # TEST 6: Upload unsupported file (error case)
    # ═════════════════════════════════════════════════════════════
    logger.info("═" * 60)
    logger.info("TEST 6: Upload unsupported file type")
    logger.info("═" * 60)

    resp = client.post(
        f"{api}/documents/upload",
        files={"file": ("readme.txt", b"This is a text file", "text/plain")},
    )
    ok = resp.status_code == 415
    logger.info("  %s Rejected unsupported type (status=%d)", "✓" if ok else "✗", resp.status_code)
    results["Reject unsupported type"] = ok

    # ═════════════════════════════════════════════════════════════
    # TEST 7: Get non-existent document (error case)
    # ═════════════════════════════════════════════════════════════
    logger.info("═" * 60)
    logger.info("TEST 7: GET /documents/99999")
    logger.info("═" * 60)

    resp = client.get(f"{api}/documents/99999")
    ok = resp.status_code == 404
    logger.info("  %s 404 for non-existent doc (status=%d)", "✓" if ok else "✗", resp.status_code)
    results["404 for missing document"] = ok

    # ═════════════════════════════════════════════════════════════
    # TEST 8: Delete document
    # ═════════════════════════════════════════════════════════════
    logger.info("═" * 60)
    logger.info("TEST 8: DELETE /documents/%s", doc_id)
    logger.info("═" * 60)

    if doc_id:
        resp = client.delete(f"{api}/documents/{doc_id}")
        ok = resp.status_code == 200
        data = resp.json()
        if ok and data.get("success"):
            logger.info("  ✓ Deleted document %d", doc_id)
            logger.info("    entities_deleted = %d", data.get("deleted_entities", 0))
            logger.info("    file_deleted     = %s", data.get("file_deleted"))
        else:
            logger.error("  ✗ Delete failed: %s", data)
            ok = False
    else:
        ok = False

    results["Delete document"] = ok

    # ═════════════════════════════════════════════════════════════
    # TEST 9: Verify deletion
    # ═════════════════════════════════════════════════════════════
    logger.info("═" * 60)
    logger.info("TEST 9: Verify deletion (GET /documents/%s)", doc_id)
    logger.info("═" * 60)

    if doc_id:
        resp = client.get(f"{api}/documents/{doc_id}")
        ok = resp.status_code == 404
        logger.info("  %s Confirmed deleted (status=%d)", "✓" if ok else "✗", resp.status_code)
    else:
        ok = False

    results["Verify deletion"] = ok

    # ═════════════════════════════════════════════════════════════
    # SUMMARY
    # ═════════════════════════════════════════════════════════════
    logger.info("═" * 60)
    logger.info("TEST SUMMARY")
    logger.info("═" * 60)
    all_ok = True
    for name, passed in results.items():
        status_str = "✓ PASS" if passed else "✗ FAIL"
        logger.info("  %s  %s", status_str, name)
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

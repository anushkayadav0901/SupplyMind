# scripts/test_risk_api.py
"""
Integration test for the Vendor Risk API (Module 5).

Uses FastAPI TestClient to exercise:
  1. Upload a document (creates a vendor)
  2. List vendors
  3. Get vendor details
  4. POST risk prediction for vendor
  5. GET risk history
  6. GET risk summary
  7. Predict again (to test history accumulation)
  8. 404 for non-existent vendor

Requires GROQ_API_KEY for document upload (extraction step).
Requires trained model at ml/models/vendor_risk_model.joblib.

Usage:
    python scripts/test_risk_api.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)-8s | %(name)-35s | %(message)s",
)
logger = logging.getLogger("test_risk_api")
logger.setLevel(logging.INFO)


def _create_sample_pdf(path: Path) -> None:
    import fitz
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    text = (
        "INVOICE #INV-2025-00500\n\n"
        "From: TestVendor ML Corp\n"
        "GSTIN: 27AAPCS1234F1ZP\n"
        "Date: 2025-06-01\n"
        "Total: 50,000\n"
    )
    page.insert_text(fitz.Point(50, 50), text, fontsize=11, fontname="helv")
    doc.save(str(path))
    doc.close()


def main() -> None:
    from fastapi.testclient import TestClient
    from backend.app.main import app
    from backend.app.config import settings
    from backend.app.database import create_all_tables

    create_all_tables()
    client = TestClient(app, raise_server_exceptions=False)
    api = settings.API_V1_STR
    results: dict[str, bool] = {}

    # ── Setup: upload a document to create a vendor ─────────────
    sample_dir = _PROJECT_ROOT / "data" / "sample_documents"
    sample_dir.mkdir(parents=True, exist_ok=True)
    pdf = sample_dir / "test_risk_invoice.pdf"
    _create_sample_pdf(pdf)

    logger.info("=" * 60)
    logger.info("SETUP: Uploading document to create vendor")
    logger.info("=" * 60)

    with open(pdf, "rb") as f:
        resp = client.post(
            f"{api}/documents/upload",
            files={"file": ("risk_test.pdf", f, "application/pdf")},
        )

    vendor_id = None
    if resp.status_code == 201 and resp.json().get("vendor_id"):
        vendor_id = resp.json()["vendor_id"]
        logger.info("  Vendor created: id=%d", vendor_id)
    else:
        logger.warning("  Upload response: %d %s", resp.status_code, resp.json().get("message", ""))
        # Fall back: create a vendor directly if upload didn't get one
        if not vendor_id:
            logger.info("  Creating vendor directly via DB...")
            from backend.app.database import SessionLocal
            from backend.app.models import Vendor
            db = SessionLocal()
            v = Vendor(name="Fallback Test Vendor", gstin="27AAPCS9999F1ZP")
            db.add(v)
            db.commit()
            vendor_id = v.id
            db.close()
            logger.info("  Fallback vendor created: id=%d", vendor_id)

    # ═══════════════════════════════════════════════════════════
    # TEST 1: List vendors
    # ═══════════════════════════════════════════════════════════
    logger.info("=" * 60)
    logger.info("TEST 1: GET /vendors")
    logger.info("=" * 60)

    resp = client.get(f"{api}/vendors")
    ok = resp.status_code == 200 and len(resp.json()) > 0
    if ok:
        logger.info("  OK: %d vendor(s) listed", len(resp.json()))
    else:
        logger.error("  FAIL: %d %s", resp.status_code, resp.text[:200])
    results["List vendors"] = ok

    # ═══════════════════════════════════════════════════════════
    # TEST 2: Get vendor details
    # ═══════════════════════════════════════════════════════════
    logger.info("=" * 60)
    logger.info("TEST 2: GET /vendors/%d", vendor_id)
    logger.info("=" * 60)

    resp = client.get(f"{api}/vendors/{vendor_id}")
    ok = resp.status_code == 200 and resp.json()["id"] == vendor_id
    if ok:
        logger.info("  OK: vendor=%s", resp.json()["name"])
    else:
        logger.error("  FAIL: %d", resp.status_code)
    results["Get vendor details"] = ok

    # ═══════════════════════════════════════════════════════════
    # TEST 3: Predict risk (First Class — high late-delivery risk)
    # ═══════════════════════════════════════════════════════════
    logger.info("=" * 60)
    logger.info("TEST 3: POST /vendors/%d/predict-risk", vendor_id)
    logger.info("=" * 60)

    resp = client.post(
        f"{api}/vendors/{vendor_id}/predict-risk",
        json={
            "features": {
                "Shipping Mode": "First Class",
                "Days for shipment (scheduled)": 1,
                "Type": "DEBIT",
                "Market": "LATAM",
                "Customer Segment": "Consumer",
                "Category Name": "Cleats",
                "Order Item Quantity": 3,
                "Order Item Discount": 5.0,
                "Order Item Discount Rate": 0.05,
                "Order Item Product Price": 120.0,
                "Sales": 360.0,
                "Order Profit Per Order": 45.0,
                "Product Price": 120.0,
            }
        },
    )

    ok = resp.status_code == 201 and "risk_label" in resp.json()
    if ok:
        data = resp.json()
        logger.info("  OK: label=%s score=%.4f prediction_id=%d",
                     data["risk_label"], data["risk_score"], data["prediction_id"])
        logger.info("  Probabilities: %s", data["probabilities"])
    else:
        logger.error("  FAIL: %d %s", resp.status_code, resp.text[:300])
    results["Predict risk"] = ok

    # ═══════════════════════════════════════════════════════════
    # TEST 4: Risk history
    # ═══════════════════════════════════════════════════════════
    logger.info("=" * 60)
    logger.info("TEST 4: GET /vendors/%d/risk-history", vendor_id)
    logger.info("=" * 60)

    resp = client.get(f"{api}/vendors/{vendor_id}/risk-history")
    ok = resp.status_code == 200 and resp.json()["prediction_count"] >= 1
    if ok:
        logger.info("  OK: %d prediction(s)", resp.json()["prediction_count"])
    else:
        logger.error("  FAIL: %d %s", resp.status_code, resp.text[:200])
    results["Risk history"] = ok

    # ═══════════════════════════════════════════════════════════
    # TEST 5: Predict again (Standard Class — low late-delivery risk)
    # ═══════════════════════════════════════════════════════════
    logger.info("=" * 60)
    logger.info("TEST 5: Second prediction (low-risk features)")
    logger.info("=" * 60)

    resp = client.post(
        f"{api}/vendors/{vendor_id}/predict-risk",
        json={
            "features": {
                "Shipping Mode": "Standard Class",
                "Days for shipment (scheduled)": 4,
                "Type": "TRANSFER",
                "Market": "Europe",
                "Customer Segment": "Corporate",
                "Category Name": "Men's Footwear",
                "Order Item Quantity": 1,
                "Order Item Discount": 0.0,
                "Order Item Discount Rate": 0.0,
                "Order Item Product Price": 50.0,
                "Sales": 50.0,
                "Order Profit Per Order": 15.0,
                "Product Price": 50.0,
            }
        },
    )

    ok = resp.status_code == 201
    if ok:
        data = resp.json()
        logger.info("  OK: label=%s score=%.4f", data["risk_label"], data["risk_score"])
    else:
        logger.error("  FAIL: %d", resp.status_code)
    results["Second prediction"] = ok

    # ═══════════════════════════════════════════════════════════
    # TEST 6: Risk summary
    # ═══════════════════════════════════════════════════════════
    logger.info("=" * 60)
    logger.info("TEST 6: GET /vendors/risk-summary")
    logger.info("=" * 60)

    resp = client.get(f"{api}/vendors/risk-summary")
    ok = resp.status_code == 200 and "distribution" in resp.json()
    if ok:
        data = resp.json()
        logger.info("  OK: total=%d distribution=%s", data["total_vendors"], data["distribution"])
    else:
        logger.error("  FAIL: %d %s", resp.status_code, resp.text[:200])
    results["Risk summary"] = ok

    # ═══════════════════════════════════════════════════════════
    # TEST 7: History should show 2 predictions
    # ═══════════════════════════════════════════════════════════
    logger.info("=" * 60)
    logger.info("TEST 7: Verify history has 2 predictions")
    logger.info("=" * 60)

    resp = client.get(f"{api}/vendors/{vendor_id}/risk-history")
    ok = resp.status_code == 200 and resp.json()["prediction_count"] >= 2
    if ok:
        logger.info("  OK: %d predictions in history", resp.json()["prediction_count"])
    else:
        logger.error("  FAIL: count=%s", resp.json().get("prediction_count"))
    results["History accumulation"] = ok

    # ═══════════════════════════════════════════════════════════
    # TEST 8: 404 for non-existent vendor
    # ═══════════════════════════════════════════════════════════
    logger.info("=" * 60)
    logger.info("TEST 8: GET /vendors/99999")
    logger.info("=" * 60)

    resp = client.get(f"{api}/vendors/99999")
    ok = resp.status_code == 404
    logger.info("  %s: 404 for missing vendor (status=%d)", "OK" if ok else "FAIL", resp.status_code)
    results["404 for missing vendor"] = ok

    # ═══════════════════════════════════════════════════════════
    # SUMMARY
    # ═══════════════════════════════════════════════════════════
    logger.info("=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    all_ok = True
    for name, passed in results.items():
        s = "PASS" if passed else "FAIL"
        logger.info("  %s  %s", s, name)
        if not passed:
            all_ok = False

    logger.info("=" * 60)
    if all_ok:
        logger.info("All tests passed!")
    else:
        logger.error("Some tests failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()

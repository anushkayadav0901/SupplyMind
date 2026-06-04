# scripts/test_ocr.py
"""
Test script for the OCR Service (Module 2).

Creates a synthetic digital PDF and a synthetic image with text,
then runs the OCR service against both to verify end-to-end
functionality.

Usage:
    python -m scripts.test_ocr              (from project root)
    python scripts/test_ocr.py              (from project root)
"""

from __future__ import annotations

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
    format="%(levelname)-8s | %(name)-30s | %(message)s",
)
logger = logging.getLogger("test_ocr")


def _create_sample_pdf(path: Path) -> None:
    """Create a simple digital PDF with procurement-style text."""
    import fitz

    doc = fitz.open()

    # Page 1 — Invoice header
    page1 = doc.new_page(width=595, height=842)  # A4
    text1 = (
        "INVOICE #INV-2025-00421\n\n"
        "From: Apex Industrial Supplies Pvt Ltd\n"
        "GSTIN: 29AABCU9603R1ZP\n"
        "Address: Plot 42, Industrial Area Phase II, Bangalore 560058\n\n"
        "To: SupplyMind Corp\n"
        "Date: 2025-06-01\n"
        "Due Date: 2025-07-01\n\n"
        "─────────────────────────────────────────────\n"
        "Item                    Qty    Unit Price    Total\n"
        "─────────────────────────────────────────────\n"
        "Hydraulic Pump HP-200    5     ₹12,500    ₹62,500\n"
        "Ball Bearing 6205-2RS   50       ₹320    ₹16,000\n"
        "Conveyor Belt CB-12M     2    ₹45,000    ₹90,000\n"
        "─────────────────────────────────────────────\n"
        "Subtotal:                              ₹1,68,500\n"
        "GST (18%):                               ₹30,330\n"
        "Total:                                 ₹1,98,830\n"
    )
    text_point = fitz.Point(50, 50)
    page1.insert_text(text_point, text1, fontsize=11, fontname="helv")

    # Page 2 — Terms & Conditions
    page2 = doc.new_page(width=595, height=842)
    text2 = (
        "TERMS & CONDITIONS\n\n"
        "1. Payment is due within 30 days of invoice date.\n"
        "2. Late payments will incur interest at 1.5% per month.\n"
        "3. Goods once sold will not be taken back.\n"
        "4. All disputes subject to Bangalore jurisdiction.\n\n"
        "Bank Details:\n"
        "Account Name: Apex Industrial Supplies Pvt Ltd\n"
        "Account No: 920020043567891\n"
        "IFSC Code: UTIB0002083\n"
        "Bank: Axis Bank, Koramangala Branch\n"
    )
    page2.insert_text(fitz.Point(50, 50), text2, fontsize=11, fontname="helv")

    doc.save(str(path))
    doc.close()
    logger.info("Created sample PDF: %s", path)


def _create_sample_image(path: Path) -> None:
    """Create a simple image with text for OCR testing."""
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (800, 400), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Use default font (available everywhere)
    try:
        font = ImageFont.truetype("arial.ttf", size=24)
    except (OSError, IOError):
        font = ImageFont.load_default()

    lines = [
        "PURCHASE ORDER #PO-2025-0078",
        "",
        "Vendor: Global Steel Works Ltd",
        "GSTIN: 27AAACG1234F1ZH",
        "Date: 2025-06-04",
        "",
        "Item: Stainless Steel Plate 304",
        "Quantity: 100 sheets",
        "Rate: Rs 2,500 per sheet",
        "Total: Rs 2,50,000",
    ]

    y = 30
    for line in lines:
        draw.text((40, y), line, fill=(0, 0, 0), font=font)
        y += 35

    img.save(str(path))
    logger.info("Created sample image: %s", path)


def test_digital_pdf(pdf_path: Path) -> bool:
    """Test extraction from a digital PDF."""
    from backend.app.services.ocr_service import OCRService

    logger.info("═" * 60)
    logger.info("TEST: Digital PDF extraction")
    logger.info("═" * 60)

    svc = OCRService()
    result = svc.extract_text(str(pdf_path))

    logger.info("Result   : %s", result.summary())
    logger.info("Method   : %s", result.extraction_method.value)
    logger.info("Pages    : %d", result.page_count)
    logger.info("Chars    : %d", result.char_count)
    logger.info("Words    : %d", result.word_count)
    logger.info("Time     : %.0f ms", result.processing_time_ms)

    # Assertions
    ok = True
    if not result.success:
        logger.error("FAIL: extraction was not successful — %s", result.error_message)
        ok = False
    if result.extraction_method.value != "pymupdf":
        logger.error("FAIL: expected pymupdf method, got %s", result.extraction_method.value)
        ok = False
    if result.page_count != 2:
        logger.error("FAIL: expected 2 pages, got %d", result.page_count)
        ok = False
    if "Apex Industrial" not in result.text:
        logger.error("FAIL: expected 'Apex Industrial' in extracted text")
        ok = False
    if "GSTIN" not in result.text:
        logger.error("FAIL: expected 'GSTIN' in extracted text")
        ok = False
    if "1,98,830" not in result.text:
        logger.error("FAIL: expected total amount in extracted text")
        ok = False

    logger.info("Preview  :\n%s\n", result.text[:400])
    return ok


def test_image_ocr(image_path: Path) -> bool:
    """Test extraction from an image."""
    from backend.app.services.ocr_service import OCRService

    logger.info("═" * 60)
    logger.info("TEST: Image OCR extraction")
    logger.info("═" * 60)

    svc = OCRService()
    result = svc.extract_text(str(image_path))

    logger.info("Result   : %s", result.summary())
    logger.info("Method   : %s", result.extraction_method.value)
    logger.info("Chars    : %d", result.char_count)
    logger.info("Conf     : %.2f%%", result.confidence * 100)
    logger.info("Time     : %.0f ms", result.processing_time_ms)

    ok = True
    if not result.success:
        logger.error("FAIL: extraction was not successful — %s", result.error_message)
        ok = False
    if result.extraction_method.value != "ocr_image":
        logger.error("FAIL: expected ocr_image method, got %s", result.extraction_method.value)
        ok = False
    if result.char_count == 0:
        logger.error("FAIL: no text extracted from image")
        ok = False

    logger.info("Preview  :\n%s\n", result.text[:400])
    return ok


def test_unsupported_file() -> bool:
    """Test that unsupported file types are handled gracefully."""
    from backend.app.services.ocr_service import OCRService

    logger.info("═" * 60)
    logger.info("TEST: Unsupported file type")
    logger.info("═" * 60)

    svc = OCRService()

    # Create a dummy .txt file
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w") as f:
        f.write("This is a text file, not a PDF or image.")
        tmp_path = f.name

    result = svc.extract_text(tmp_path)

    ok = True
    if result.success:
        logger.error("FAIL: expected failure for unsupported type")
        ok = False
    if "Unsupported file type" not in (result.error_message or ""):
        logger.error("FAIL: expected 'Unsupported file type' in error message")
        ok = False

    logger.info("Correctly rejected: %s", result.error_message)
    Path(tmp_path).unlink(missing_ok=True)
    return ok


def test_missing_file() -> bool:
    """Test that missing files are handled gracefully."""
    from backend.app.services.ocr_service import OCRService

    logger.info("═" * 60)
    logger.info("TEST: Missing file")
    logger.info("═" * 60)

    svc = OCRService()
    result = svc.extract_text("/nonexistent/file.pdf")

    ok = True
    if result.success:
        logger.error("FAIL: expected failure for missing file")
        ok = False
    if "not found" not in (result.error_message or "").lower():
        logger.error("FAIL: expected 'not found' in error message")
        ok = False

    logger.info("Correctly rejected: %s", result.error_message)
    return ok


def test_helper_methods(pdf_path: Path, image_path: Path) -> bool:
    """Test static helper methods."""
    from backend.app.services.ocr_service import OCRService

    logger.info("═" * 60)
    logger.info("TEST: Helper methods")
    logger.info("═" * 60)

    ok = True

    # Page count
    pdf_pages = OCRService.get_page_count(str(pdf_path))
    if pdf_pages != 2:
        logger.error("FAIL: expected 2 pages for PDF, got %d", pdf_pages)
        ok = False
    else:
        logger.info("PDF page count: %d ✓", pdf_pages)

    img_pages = OCRService.get_page_count(str(image_path))
    if img_pages != 1:
        logger.error("FAIL: expected 1 page for image, got %d", img_pages)
        ok = False
    else:
        logger.info("Image page count: %d ✓", img_pages)

    # Supported check
    if not OCRService.is_supported(str(pdf_path)):
        logger.error("FAIL: PDF should be supported")
        ok = False
    if not OCRService.is_supported(str(image_path)):
        logger.error("FAIL: PNG should be supported")
        ok = False
    if OCRService.is_supported("file.txt"):
        logger.error("FAIL: TXT should not be supported")
        ok = False

    logger.info("Supported extensions: %s", OCRService.supported_extensions())
    return ok


def main() -> None:
    """Run all OCR tests."""

    # Set up sample files in the project's data directory
    data_dir = _PROJECT_ROOT / "data" / "sample_documents"
    data_dir.mkdir(parents=True, exist_ok=True)

    pdf_path = data_dir / "test_invoice.pdf"
    image_path = data_dir / "test_purchase_order.png"

    # Generate test files
    _create_sample_pdf(pdf_path)
    _create_sample_image(image_path)

    # Run tests
    results = {
        "Digital PDF": test_digital_pdf(pdf_path),
        "Image OCR": test_image_ocr(image_path),
        "Unsupported file": test_unsupported_file(),
        "Missing file": test_missing_file(),
        "Helper methods": test_helper_methods(pdf_path, image_path),
    }

    # Summary
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

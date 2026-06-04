# backend/app/services/ocr_service.py
"""
OCR Service — extracts text from PDFs and images.

Supports three document types:

  1. Digital PDFs   → PyMuPDF direct text extraction (fast, accurate)
  2. Scanned PDFs   → PyMuPDF page→image rendering + EasyOCR
  3. Images         → EasyOCR directly

Auto-detection strategy:
  - Attempt PyMuPDF text extraction first.
  - If extracted text is below a character-per-page threshold,
    treat the PDF as scanned and fall back to OCR.

Usage::

    from backend.app.services.ocr_service import OCRService

    service = OCRService()
    result  = service.extract_text("path/to/invoice.pdf")
    print(result.text, result.extraction_method, result.page_count)
"""

from __future__ import annotations

import logging
import mimetypes
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import ClassVar, List, Optional

import fitz  # PyMuPDF
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


# =====================================================================
#  Constants
# =====================================================================

# If a PDF page yields fewer than this many characters from PyMuPDF,
# we consider it scanned/image-based and fall back to OCR.
_MIN_CHARS_PER_PAGE: int = 30

# DPI for rendering PDF pages to images before OCR.
# 300 DPI is the sweet spot between quality and speed.
_RENDER_DPI: int = 300

# Supported MIME types
_PDF_MIME_TYPES = {"application/pdf"}
_IMAGE_MIME_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/tiff", "image/bmp", "image/webp"}
_SUPPORTED_MIME_TYPES = _PDF_MIME_TYPES | _IMAGE_MIME_TYPES


# =====================================================================
#  Extraction Method Enum
# =====================================================================

class ExtractionMethod(str, Enum):
    """How the text was extracted."""

    PYMUPDF = "pymupdf"          # Digital PDF — direct text extraction
    OCR_SCANNED_PDF = "ocr_scanned_pdf"  # Scanned PDF — page render + EasyOCR
    OCR_IMAGE = "ocr_image"      # Standalone image — EasyOCR
    NONE = "none"                # No extraction performed


# =====================================================================
#  OCR Result Dataclass
# =====================================================================

@dataclass
class OCRResult:
    """Structured output from the OCR pipeline."""

    text: str = ""
    extraction_method: ExtractionMethod = ExtractionMethod.NONE
    page_count: int = 0
    confidence: float = 0.0
    processing_time_ms: float = 0.0
    success: bool = False
    error_message: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    @property
    def char_count(self) -> int:
        return len(self.text)

    @property
    def word_count(self) -> int:
        return len(self.text.split()) if self.text else 0

    def summary(self) -> str:
        """Human-readable one-liner."""
        status = "OK" if self.success else f"FAILED ({self.error_message})"
        return (
            f"[{status}] method={self.extraction_method.value} "
            f"pages={self.page_count} chars={self.char_count} "
            f"words={self.word_count} time={self.processing_time_ms:.0f}ms"
        )


# =====================================================================
#  OCR Service
# =====================================================================

class OCRService:
    """Unified text extraction service for PDFs and images.

    Lazily initialises the EasyOCR reader on first use (the model
    download + load is expensive, so we only pay the cost if OCR is
    actually needed).

    Parameters
    ----------
    languages : list[str]
        Language codes for EasyOCR (default ``["en"]``).
    gpu : bool
        Whether EasyOCR should use GPU acceleration.
    min_chars_per_page : int
        Threshold for digital-vs-scanned PDF detection.
    render_dpi : int
        Resolution when rasterising PDF pages for OCR.
    """

    # Class-level EasyOCR reader cache — shared across all instances
    # so the model is loaded at most once per process.
    _easyocr_reader: ClassVar[Optional[object]] = None
    _easyocr_languages: ClassVar[List[str]] = []
    _easyocr_gpu: ClassVar[bool] = False

    def __init__(
        self,
        languages: Optional[List[str]] = None,
        gpu: bool = False,
        min_chars_per_page: int = _MIN_CHARS_PER_PAGE,
        render_dpi: int = _RENDER_DPI,
    ) -> None:
        self.languages = languages or ["en"]
        self.gpu = gpu
        self.min_chars_per_page = min_chars_per_page
        self.render_dpi = render_dpi

    # ─────────────────────────────────────────────────────────────
    #  Lazy EasyOCR initialisation
    # ─────────────────────────────────────────────────────────────

    def _get_reader(self):  # noqa: ANN202
        """Return the cached EasyOCR reader, creating it on first call."""
        if (
            OCRService._easyocr_reader is None
            or OCRService._easyocr_languages != self.languages
            or OCRService._easyocr_gpu != self.gpu
        ):
            import easyocr  # deferred import — heavy dependency

            logger.info(
                "Initialising EasyOCR reader (languages=%s, gpu=%s) …",
                self.languages,
                self.gpu,
            )
            OCRService._easyocr_reader = easyocr.Reader(
                self.languages,
                gpu=self.gpu,
                verbose=False,
            )
            OCRService._easyocr_languages = list(self.languages)
            OCRService._easyocr_gpu = self.gpu
            logger.info("EasyOCR reader ready.")

        return OCRService._easyocr_reader

    # ─────────────────────────────────────────────────────────────
    #  Public API
    # ─────────────────────────────────────────────────────────────

    def extract_text(self, file_path: str) -> OCRResult:
        """Extract text from a PDF or image file.

        Automatically detects the file type and chooses the best
        extraction strategy.

        Parameters
        ----------
        file_path : str
            Absolute or relative path to the document.

        Returns
        -------
        OCRResult
            Structured result with text, method, metadata, etc.
        """
        start = time.perf_counter()
        path = Path(file_path)

        # ── Validate file exists ────────────────────────────────
        if not path.exists():
            return OCRResult(
                success=False,
                error_message=f"File not found: {path}",
            )

        if not path.is_file():
            return OCRResult(
                success=False,
                error_message=f"Path is not a file: {path}",
            )

        # ── Detect MIME type ────────────────────────────────────
        mime_type = self._detect_mime_type(path)

        if mime_type not in _SUPPORTED_MIME_TYPES:
            return OCRResult(
                success=False,
                error_message=(
                    f"Unsupported file type: {mime_type}. "
                    f"Supported: {sorted(_SUPPORTED_MIME_TYPES)}"
                ),
            )

        # ── Route to the appropriate extractor ──────────────────
        try:
            if mime_type in _PDF_MIME_TYPES:
                result = self._process_pdf(path)
            else:
                result = self._extract_image_text(path)
        except Exception as exc:
            logger.exception("OCR failed for %s", path)
            return OCRResult(
                success=False,
                error_message=f"Extraction error: {exc}",
                metadata={"file": str(path), "mime_type": mime_type},
            )

        # ── Finalise timing ─────────────────────────────────────
        elapsed_ms = (time.perf_counter() - start) * 1000
        result.processing_time_ms = elapsed_ms
        result.metadata["file"] = str(path)
        result.metadata["mime_type"] = mime_type

        logger.info("OCR complete: %s", result.summary())
        return result

    # ─────────────────────────────────────────────────────────────
    #  PDF processing (auto-detect digital vs scanned)
    # ─────────────────────────────────────────────────────────────

    def _process_pdf(self, path: Path) -> OCRResult:
        """Open a PDF and decide between direct extraction and OCR."""
        doc = fitz.open(str(path))
        page_count = len(doc)

        try:
            if self._is_digital_pdf(doc):
                return self._extract_pdf_text(doc, page_count)
            else:
                return self._extract_scanned_pdf(doc, page_count)
        finally:
            doc.close()

    def _is_digital_pdf(self, doc: fitz.Document) -> bool:
        """Return True if the PDF contains sufficient selectable text.

        Checks every page — if *any* page is below the character
        threshold we treat the entire document as scanned, because
        mixed digital/scanned PDFs are common in procurement
        (e.g. a cover letter followed by a scanned invoice).
        """
        if len(doc) == 0:
            return False

        total_chars = 0
        for page in doc:
            text = page.get_text("text").strip()
            total_chars += len(text)

        avg_chars_per_page = total_chars / len(doc)
        is_digital = avg_chars_per_page >= self.min_chars_per_page

        logger.debug(
            "PDF digital check: total_chars=%d, pages=%d, avg=%.1f, is_digital=%s",
            total_chars,
            len(doc),
            avg_chars_per_page,
            is_digital,
        )
        return is_digital

    # ─────────────────────────────────────────────────────────────
    #  Digital PDF extraction
    # ─────────────────────────────────────────────────────────────

    def _extract_pdf_text(self, doc: fitz.Document, page_count: int) -> OCRResult:
        """Extract text directly from a digital PDF using PyMuPDF."""
        pages_text: List[str] = []

        for page_num, page in enumerate(doc):
            text = page.get_text("text").strip()
            if text:
                pages_text.append(text)
            logger.debug("Page %d: %d chars extracted (PyMuPDF)", page_num + 1, len(text))

        combined = "\n\n".join(pages_text)

        return OCRResult(
            text=self._clean_text(combined),
            extraction_method=ExtractionMethod.PYMUPDF,
            page_count=page_count,
            confidence=1.0,  # Direct extraction is deterministic
            success=True,
            metadata={"pages_with_text": len(pages_text)},
        )

    # ─────────────────────────────────────────────────────────────
    #  Scanned PDF extraction (render → OCR)
    # ─────────────────────────────────────────────────────────────

    def _extract_scanned_pdf(self, doc: fitz.Document, page_count: int) -> OCRResult:
        """Render each page of a scanned PDF to an image and run OCR."""
        reader = self._get_reader()
        pages_text: List[str] = []
        all_confidences: List[float] = []

        # Compute the zoom factor from DPI (PyMuPDF default is 72 DPI)
        zoom = self.render_dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)

        for page_num, page in enumerate(doc):
            # Render page to a pixmap (RGB)
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)

            # Convert pixmap → numpy array for EasyOCR
            img_array = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(
                pixmap.height, pixmap.width, 3
            )

            # Run OCR
            results = reader.readtext(img_array, detail=1)
            page_text_parts: List[str] = []
            for bbox, text, conf in results:
                page_text_parts.append(text)
                all_confidences.append(conf)

            page_text = " ".join(page_text_parts).strip()
            if page_text:
                pages_text.append(page_text)

            logger.debug(
                "Page %d: %d chars extracted (EasyOCR, %d detections)",
                page_num + 1,
                len(page_text),
                len(results),
            )

        combined = "\n\n".join(pages_text)
        avg_conf = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0

        return OCRResult(
            text=self._clean_text(combined),
            extraction_method=ExtractionMethod.OCR_SCANNED_PDF,
            page_count=page_count,
            confidence=round(avg_conf, 4),
            success=True,
            metadata={
                "pages_with_text": len(pages_text),
                "total_detections": len(all_confidences),
                "render_dpi": self.render_dpi,
            },
        )

    # ─────────────────────────────────────────────────────────────
    #  Image extraction
    # ─────────────────────────────────────────────────────────────

    def _extract_image_text(self, path: Path) -> OCRResult:
        """Extract text from a standalone image file using EasyOCR."""
        reader = self._get_reader()

        # Validate the image can be opened
        img = Image.open(path)
        img.verify()  # checks for corruption
        # Re-open after verify (verify closes the file)
        img = Image.open(path)

        # Convert to RGB if needed (e.g. RGBA PNGs, grayscale)
        if img.mode != "RGB":
            img = img.convert("RGB")

        img_array = np.array(img)

        results = reader.readtext(img_array, detail=1)

        text_parts: List[str] = []
        confidences: List[float] = []
        for bbox, text, conf in results:
            text_parts.append(text)
            confidences.append(conf)

        combined = " ".join(text_parts).strip()
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

        return OCRResult(
            text=self._clean_text(combined),
            extraction_method=ExtractionMethod.OCR_IMAGE,
            page_count=1,
            confidence=round(avg_conf, 4),
            success=True,
            metadata={
                "image_size": list(img.size),
                "image_mode": img.mode,
                "total_detections": len(results),
            },
        )

    # ─────────────────────────────────────────────────────────────
    #  Helpers
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def _detect_mime_type(path: Path) -> str:
        """Detect MIME type from extension, with .pdf special-casing."""
        suffix = path.suffix.lower()

        # Explicit mapping for common procurement file types
        explicit = {
            ".pdf": "application/pdf",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".tiff": "image/tiff",
            ".tif": "image/tiff",
            ".bmp": "image/bmp",
            ".webp": "image/webp",
        }
        if suffix in explicit:
            return explicit[suffix]

        # Fallback to stdlib
        guessed, _ = mimetypes.guess_type(str(path))
        return guessed or "application/octet-stream"

    @staticmethod
    def _clean_text(text: str) -> str:
        """Normalise extracted text.

        - Collapse runs of whitespace to single spaces / newlines.
        - Strip leading/trailing whitespace from each line.
        - Remove completely blank lines (more than two consecutive).
        """
        lines = text.splitlines()
        cleaned: List[str] = []
        blank_count = 0

        for line in lines:
            stripped = " ".join(line.split())  # collapse internal whitespace
            if not stripped:
                blank_count += 1
                if blank_count <= 1:
                    cleaned.append("")
            else:
                blank_count = 0
                cleaned.append(stripped)

        return "\n".join(cleaned).strip()

    @staticmethod
    def get_page_count(file_path: str) -> int:
        """Return page count for a PDF, or 1 for images.

        Useful as a lightweight metadata probe without full extraction.
        """
        path = Path(file_path)
        suffix = path.suffix.lower()

        if suffix == ".pdf":
            doc = fitz.open(str(path))
            count = len(doc)
            doc.close()
            return count

        return 1

    @staticmethod
    def is_supported(file_path: str) -> bool:
        """Check whether the file type is supported by this service."""
        path = Path(file_path)
        mime = OCRService._detect_mime_type(path)
        return mime in _SUPPORTED_MIME_TYPES

    @staticmethod
    def supported_extensions() -> List[str]:
        """Return a list of supported file extensions."""
        return [".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".webp"]


# =====================================================================
#  Convenience — module-level singleton
# =====================================================================
# Import and use directly:  from backend.app.services.ocr_service import ocr_service
ocr_service = OCRService()


# =====================================================================
#  CLI entry point for quick testing
# =====================================================================
if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s | %(name)s | %(message)s")

    if len(sys.argv) < 2:
        print("Usage: python -m backend.app.services.ocr_service <file_path>")
        sys.exit(1)

    target = sys.argv[1]
    print(f"\nProcessing: {target}\n{'─' * 60}")

    svc = OCRService()
    result = svc.extract_text(target)

    print(f"Status     : {'✓ Success' if result.success else '✗ Failed'}")
    print(f"Method     : {result.extraction_method.value}")
    print(f"Pages      : {result.page_count}")
    print(f"Characters : {result.char_count}")
    print(f"Words      : {result.word_count}")
    print(f"Confidence : {result.confidence:.2%}")
    print(f"Time       : {result.processing_time_ms:.0f} ms")
    if result.error_message:
        print(f"Error      : {result.error_message}")
    print(f"{'─' * 60}")
    print(f"\nExtracted text (first 500 chars):\n")
    print(result.text[:500] if result.text else "(empty)")
    print()

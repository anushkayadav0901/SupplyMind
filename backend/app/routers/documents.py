# backend/app/routers/documents.py
"""
Document upload, listing, detail, and deletion API.

This is the first end-to-end business workflow in SupplyMind:

    Upload file  →  OCR  →  Entity extraction  →  DB persistence  →  Response

All heavy lifting is delegated to:
  - OCRService          (Module 2)
  - ExtractionService   (Module 3)

The router is kept thin — helper functions handle file I/O, DB
record creation, and response building.
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.dependencies import DbSession
from backend.app.models import Document, ExtractedEntity, OCRStatus, Vendor
from backend.app.schemas import (
    DocumentDeleteResponse,
    DocumentListItem,
    DocumentRead,
    DocumentUploadResponse,
    ExtractionSummary,
    VendorSummary,
)
from backend.app.services.extraction_service import ExtractionResult, ExtractionService
from backend.app.services.ocr_service import OCRResult, OCRService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


# =====================================================================
#  Service singletons (lazy-loaded, shared across requests)
# =====================================================================

_ocr_service: Optional[OCRService] = None
_extraction_service: Optional[ExtractionService] = None


def _get_ocr_service() -> OCRService:
    global _ocr_service
    if _ocr_service is None:
        _ocr_service = OCRService()
    return _ocr_service


def _get_extraction_service() -> ExtractionService:
    global _extraction_service
    if _extraction_service is None:
        _extraction_service = ExtractionService()
    return _extraction_service


# =====================================================================
#  File helpers
# =====================================================================

def _generate_stored_filename(original: str) -> str:
    """Generate a unique, safe filename for storage.

    Format: ``<uuid4>_<sanitised_original>``
    """
    safe = original.replace(" ", "_").replace("/", "_").replace("\\", "_")
    # Keep only alnum, dots, hyphens, underscores
    safe = "".join(c for c in safe if c.isalnum() or c in "._-")
    # Limit length of the original portion
    if len(safe) > 120:
        suffix = Path(safe).suffix
        safe = safe[:120 - len(suffix)] + suffix
    return f"{uuid.uuid4().hex[:12]}_{safe}"


def _save_upload(file: UploadFile, stored_filename: str) -> tuple[Path, int]:
    """Save the uploaded file to the configured upload directory.

    Returns (file_path, file_size_bytes).
    """
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    dest = upload_dir / stored_filename
    content = file.file.read()
    dest.write_bytes(content)

    return dest, len(content)


def _delete_file(file_path: str) -> bool:
    """Delete a file from disk. Returns True if deleted, False otherwise."""
    try:
        p = Path(file_path)
        if p.exists() and p.is_file():
            p.unlink()
            return True
    except OSError as exc:
        logger.warning("Failed to delete file %s: %s", file_path, exc)
    return False


# =====================================================================
#  DB helpers
# =====================================================================

def _create_document(
    db: Session,
    *,
    original_filename: str,
    stored_filename: str,
    file_path: str,
    mime_type: str,
    file_size: int,
) -> Document:
    """Create a Document row with PENDING status."""
    doc = Document(
        filename=stored_filename,
        original_filename=original_filename,
        file_path=file_path,
        mime_type=mime_type,
        file_size=file_size,
        ocr_status=OCRStatus.PENDING,
    )
    db.add(doc)
    db.flush()  # get the id without committing
    return doc


def _update_document_after_ocr(
    doc: Document,
    ocr_result: OCRResult,
) -> None:
    """Update Document fields with OCR results."""
    if ocr_result.success:
        doc.extracted_text = ocr_result.text
        doc.ocr_status = OCRStatus.COMPLETED
        doc.ocr_method = ocr_result.extraction_method.value
        doc.page_count = ocr_result.page_count
    else:
        doc.ocr_status = OCRStatus.FAILED
        doc.ocr_method = None
        doc.page_count = 0


def _find_or_create_vendor(
    db: Session,
    extraction: ExtractionResult,
) -> Optional[Vendor]:
    """Find an existing vendor by GSTIN or create a new one.

    Returns None if no vendor name was extracted.
    """
    if not extraction.vendor_name:
        return None

    # Try to find by GSTIN first (unique identifier)
    if extraction.vendor_gstin:
        existing = (
            db.query(Vendor)
            .filter(Vendor.gstin == extraction.vendor_gstin)
            .first()
        )
        if existing:
            # Update fields if new info is available
            if extraction.contact_email and not existing.contact_email:
                existing.contact_email = extraction.contact_email
            if extraction.contact_phone and not existing.contact_phone:
                existing.contact_phone = extraction.contact_phone
            if extraction.vendor_address and not existing.address:
                existing.address = extraction.vendor_address
            return existing

    # Try by name (case-insensitive)
    existing = (
        db.query(Vendor)
        .filter(Vendor.name == extraction.vendor_name)
        .first()
    )
    if existing:
        # Enrich with any new data
        if extraction.vendor_gstin and not existing.gstin:
            existing.gstin = extraction.vendor_gstin
        if extraction.vendor_pan and not existing.pan:
            existing.pan = extraction.vendor_pan
        if extraction.contact_email and not existing.contact_email:
            existing.contact_email = extraction.contact_email
        if extraction.contact_phone and not existing.contact_phone:
            existing.contact_phone = extraction.contact_phone
        if extraction.vendor_address and not existing.address:
            existing.address = extraction.vendor_address
        return existing

    # Create new vendor
    vendor = Vendor(
        name=extraction.vendor_name,
        gstin=extraction.vendor_gstin,
        pan=extraction.vendor_pan,
        contact_email=extraction.contact_email,
        contact_phone=extraction.contact_phone,
        address=extraction.vendor_address,
    )
    db.add(vendor)
    db.flush()
    return vendor


def _create_extracted_entity(
    db: Session,
    *,
    document_id: int,
    vendor_id: Optional[int],
    extraction: ExtractionResult,
) -> ExtractedEntity:
    """Create an ExtractedEntity row from the extraction result."""
    entity = ExtractedEntity(
        document_id=document_id,
        vendor_id=vendor_id,
        entity_type=extraction.document_type or "unknown",
        entity_data=extraction.to_entity_data(),
        confidence_score=extraction.confidence_score,
    )
    db.add(entity)
    db.flush()
    return entity


# =====================================================================
#  Response builders
# =====================================================================

def _build_extraction_summary(extraction: ExtractionResult) -> ExtractionSummary:
    """Build a compact extraction summary for the API response."""
    return ExtractionSummary(
        document_type=extraction.document_type,
        document_number=extraction.document_number,
        vendor_name=extraction.vendor_name,
        vendor_gstin=extraction.vendor_gstin,
        total_amount=extraction.total_amount,
        currency=extraction.currency,
        line_item_count=len(extraction.line_items),
        confidence_score=extraction.confidence_score,
    )


def _build_vendor_summary(vendor: Optional[Vendor]) -> Optional[VendorSummary]:
    """Build a vendor summary, or None if no vendor."""
    if vendor is None:
        return None
    return VendorSummary(
        id=vendor.id,
        name=vendor.name,
        gstin=vendor.gstin,
    )


# =====================================================================
#  POST /documents/upload
# =====================================================================

@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and process a procurement document",
    description=(
        "Accepts a PDF or image file, runs OCR to extract text, "
        "then uses AI to extract structured procurement entities. "
        "Results are persisted to the database."
    ),
)
def upload_document(
    file: UploadFile,
    db: DbSession,
) -> DocumentUploadResponse:
    """Full upload → OCR → extraction → persist pipeline."""

    # ── 1. Validate file type ───────────────────────────────────
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided.",
        )

    if not OCRService.is_supported(file.filename):
        supported = OCRService.supported_extensions()
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported file type: '{Path(file.filename).suffix}'. "
                f"Supported: {supported}"
            ),
        )

    # ── 2. Save file to disk ───────────────────────────────────
    stored_filename = _generate_stored_filename(file.filename)

    try:
        file_path, file_size = _save_upload(file, stored_filename)
    except Exception as exc:
        logger.exception("Failed to save uploaded file: %s", file.filename)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {exc}",
        )

    # ── 3. Create Document row (PENDING) ───────────────────────
    mime_type = file.content_type or "application/octet-stream"
    doc = _create_document(
        db,
        original_filename=file.filename,
        stored_filename=stored_filename,
        file_path=str(file_path),
        mime_type=mime_type,
        file_size=file_size,
    )

    # ── 4. Run OCR ─────────────────────────────────────────────
    ocr_svc = _get_ocr_service()
    ocr_result = ocr_svc.extract_text(str(file_path))
    _update_document_after_ocr(doc, ocr_result)

    if not ocr_result.success:
        db.commit()
        return DocumentUploadResponse(
            success=False,
            message=f"OCR failed: {ocr_result.error_message}",
            document_id=doc.id,
            original_filename=file.filename,
            stored_filename=stored_filename,
            mime_type=mime_type,
            file_size=file_size,
            ocr_status=doc.ocr_status.value,
            ocr_method=None,
            text_length=0,
        )

    # ── 5. Run entity extraction ───────────────────────────────
    ext_svc = _get_extraction_service()
    extraction = ext_svc.extract_entities(ocr_result.text, document_id=doc.id)

    # ── 6. Persist vendor (find or create) ─────────────────────
    vendor: Optional[Vendor] = None
    try:
        vendor = _find_or_create_vendor(db, extraction)
    except Exception as exc:
        logger.warning("Vendor persistence failed (doc=%d): %s", doc.id, exc)

    # ── 7. Persist extracted entity ────────────────────────────
    entity: Optional[ExtractedEntity] = None
    try:
        entity = _create_extracted_entity(
            db,
            document_id=doc.id,
            vendor_id=vendor.id if vendor else None,
            extraction=extraction,
        )
    except Exception as exc:
        logger.warning("Entity persistence failed (doc=%d): %s", doc.id, exc)

    # ── 8. Commit everything ───────────────────────────────────
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception("DB commit failed for doc=%d", doc.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {exc}",
        )

    # ── 9. Build response ──────────────────────────────────────
    logger.info(
        "Document processed: id=%d file=%s vendor=%s",
        doc.id,
        file.filename,
        extraction.vendor_name or "N/A",
    )

    return DocumentUploadResponse(
        success=True,
        message="Document processed successfully.",
        document_id=doc.id,
        entity_id=entity.id if entity else None,
        vendor_id=vendor.id if vendor else None,
        original_filename=file.filename,
        stored_filename=stored_filename,
        mime_type=mime_type,
        file_size=file_size,
        page_count=doc.page_count,
        ocr_status=doc.ocr_status.value,
        ocr_method=doc.ocr_method,
        text_length=len(ocr_result.text),
        extraction=_build_extraction_summary(extraction),
        vendor=_build_vendor_summary(vendor),
    )


# =====================================================================
#  GET /documents
# =====================================================================

@router.get(
    "",
    response_model=List[DocumentListItem],
    summary="List all uploaded documents",
)
def list_documents(
    db: DbSession,
    skip: int = 0,
    limit: int = 50,
) -> list:
    """Return a paginated list of documents, newest first."""
    docs = (
        db.query(Document)
        .order_by(Document.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    result = []
    for doc in docs:
        item = DocumentListItem(
            id=doc.id,
            original_filename=doc.original_filename,
            filename=doc.filename,
            mime_type=doc.mime_type,
            file_size=doc.file_size,
            page_count=doc.page_count,
            ocr_status=doc.ocr_status.value,
            ocr_method=doc.ocr_method,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
            entity_count=len(doc.extracted_entities),
        )
        result.append(item)

    return result


# =====================================================================
#  GET /documents/{document_id}
# =====================================================================

@router.get(
    "/{document_id}",
    response_model=DocumentRead,
    summary="Get full document details",
)
def get_document(
    document_id: int,
    db: DbSession,
) -> Document:
    """Return complete document details including extracted entities."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found.",
        )
    return doc


# =====================================================================
#  GET /documents/{document_id}/raw-text
# =====================================================================

@router.get(
    "/{document_id}/raw-text",
    summary="Get the raw OCR text of a document",
)
def get_document_raw_text(
    document_id: int,
    db: DbSession,
) -> dict:
    """Return the raw extracted text (useful for debugging / RAG input)."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found.",
        )

    return {
        "document_id": doc.id,
        "original_filename": doc.original_filename,
        "ocr_status": doc.ocr_status.value,
        "ocr_method": doc.ocr_method,
        "text_length": len(doc.extracted_text) if doc.extracted_text else 0,
        "text": doc.extracted_text or "",
    }


# =====================================================================
#  GET /documents/{document_id}/entities
# =====================================================================

@router.get(
    "/{document_id}/entities",
    summary="Get structured extracted entities for a document",
)
def get_document_entities(
    document_id: int,
    db: DbSession,
) -> dict:
    """Return the structured entity data extracted from this document."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found.",
        )

    entities = []
    for ent in doc.extracted_entities:
        vendor_info = None
        if ent.vendor:
            vendor_info = {
                "id": ent.vendor.id,
                "name": ent.vendor.name,
                "gstin": ent.vendor.gstin,
            }
        entities.append({
            "id": ent.id,
            "entity_type": ent.entity_type,
            "confidence_score": ent.confidence_score,
            "entity_data": ent.entity_data,
            "vendor": vendor_info,
            "created_at": ent.created_at.isoformat(),
        })

    return {
        "document_id": doc.id,
        "original_filename": doc.original_filename,
        "entity_count": len(entities),
        "entities": entities,
    }


# =====================================================================
#  DELETE /documents/{document_id}
# =====================================================================

@router.delete(
    "/{document_id}",
    response_model=DocumentDeleteResponse,
    summary="Delete a document and its related data",
)
def delete_document(
    document_id: int,
    db: DbSession,
) -> DocumentDeleteResponse:
    """Delete a document, its extracted entities, and the uploaded file."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found.",
        )

    # Count entities before cascade delete
    entity_count = len(doc.extracted_entities)

    # Delete file from disk
    file_deleted = _delete_file(doc.file_path)

    # Delete DB record (cascade deletes extracted_entities)
    db.delete(doc)

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to delete document %d", document_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {exc}",
        )

    return DocumentDeleteResponse(
        success=True,
        message=f"Document {document_id} deleted.",
        document_id=document_id,
        deleted_entities=entity_count,
        file_deleted=file_deleted,
    )

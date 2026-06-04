# backend/app/schemas.py
"""
Pydantic v2 schemas for the API layer.

Naming convention:
  - *Base     → shared fields (used as a mixin, never exposed directly)
  - *Create   → request body for creation
  - *Update   → request body for partial updates
  - *Read     → response model (includes id, timestamps, relations)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# =====================================================================
#  Health
# =====================================================================
class HealthResponse(BaseModel):
    status: str = Field(..., examples=["ok"])
    service: str
    version: str
    database: str = Field(..., examples=["connected"])
    timestamp: datetime


# =====================================================================
#  Document
# =====================================================================
class DocumentBase(BaseModel):
    original_filename: str
    mime_type: str

class DocumentCreate(DocumentBase):
    """Fields supplied by the upload handler (not directly by the user)."""
    filename: str
    file_path: str
    file_size: Optional[int] = None
    page_count: Optional[int] = None

class DocumentUpdate(BaseModel):
    """Partial update — every field optional."""
    extracted_text: Optional[str] = None
    ocr_status: Optional[str] = None
    ocr_method: Optional[str] = None
    page_count: Optional[int] = None

class DocumentRead(DocumentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    file_path: str
    file_size: Optional[int] = None
    page_count: Optional[int] = None
    extracted_text: Optional[str] = None
    ocr_status: str
    ocr_method: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    extracted_entities: List[ExtractedEntityRead] = []

class DocumentListItem(BaseModel):
    """Lightweight schema for list views — omits extracted_text."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_filename: str
    filename: str
    mime_type: str
    file_size: Optional[int] = None
    page_count: Optional[int] = None
    ocr_status: str
    ocr_method: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    entity_count: int = 0


# =====================================================================
#  Vendor
# =====================================================================
class VendorBase(BaseModel):
    name: str
    gstin: Optional[str] = None
    pan: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    website: Optional[str] = None

class VendorCreate(VendorBase):
    pass

class VendorUpdate(BaseModel):
    name: Optional[str] = None
    gstin: Optional[str] = None
    pan: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    website: Optional[str] = None

class VendorRead(VendorBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
    risk_predictions: List[RiskPredictionRead] = []

class VendorSummary(BaseModel):
    """Minimal vendor info for embedding in upload responses."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    gstin: Optional[str] = None


# =====================================================================
#  Extracted Entity
# =====================================================================
class ExtractedEntityBase(BaseModel):
    entity_type: str
    entity_data: Dict[str, Any] = Field(default_factory=dict)
    confidence_score: Optional[float] = None

class ExtractedEntityCreate(ExtractedEntityBase):
    document_id: int
    vendor_id: Optional[int] = None

class ExtractedEntityRead(ExtractedEntityBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    vendor_id: Optional[int] = None
    created_at: datetime


# =====================================================================
#  Risk Prediction
# =====================================================================
class RiskPredictionBase(BaseModel):
    risk_score: float = Field(..., ge=0.0, le=1.0)
    risk_label: str
    model_version: str

class RiskPredictionCreate(RiskPredictionBase):
    vendor_id: int
    feature_payload: Optional[Dict[str, Any]] = None

class RiskPredictionRead(RiskPredictionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vendor_id: int
    feature_payload: Optional[Dict[str, Any]] = None
    predicted_at: datetime


# =====================================================================
#  Document Upload Response (Module 4)
# =====================================================================
class ExtractionSummary(BaseModel):
    """Compact extraction summary for the upload response."""
    document_type: Optional[str] = None
    document_number: Optional[str] = None
    vendor_name: Optional[str] = None
    vendor_gstin: Optional[str] = None
    total_amount: Optional[float] = None
    currency: Optional[str] = None
    line_item_count: int = 0
    confidence_score: float = 0.0

class DocumentUploadResponse(BaseModel):
    """Response returned after a successful document upload + processing."""
    success: bool = True
    message: str = "Document processed successfully."

    # IDs
    document_id: int
    entity_id: Optional[int] = None
    vendor_id: Optional[int] = None

    # Document metadata
    original_filename: str
    stored_filename: str
    mime_type: str
    file_size: Optional[int] = None
    page_count: Optional[int] = None

    # OCR info
    ocr_status: str
    ocr_method: Optional[str] = None
    text_length: int = 0

    # Extraction summary
    extraction: Optional[ExtractionSummary] = None

    # Vendor summary
    vendor: Optional[VendorSummary] = None

class DocumentDeleteResponse(BaseModel):
    """Response returned after deleting a document."""
    success: bool = True
    message: str
    document_id: int
    deleted_entities: int = 0
    file_deleted: bool = False


# =====================================================================
#  Rebuild forward refs (DocumentRead ↔ ExtractedEntityRead, etc.)
# =====================================================================
DocumentRead.model_rebuild()
VendorRead.model_rebuild()

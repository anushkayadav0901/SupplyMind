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
    created_at: datetime
    updated_at: datetime
    extracted_entities: List[ExtractedEntityRead] = []


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
#  Rebuild forward refs (DocumentRead ↔ ExtractedEntityRead, etc.)
# =====================================================================
DocumentRead.model_rebuild()
VendorRead.model_rebuild()

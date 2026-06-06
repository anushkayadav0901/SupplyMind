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
#  Vendor List / Detail (Module 5)
# =====================================================================
class VendorListItem(BaseModel):
    """Vendor row for list views — includes latest risk status."""
    id: int
    name: str
    gstin: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    latest_risk_label: Optional[str] = None
    latest_risk_score: Optional[float] = None
    prediction_count: int = 0
    document_count: int = 0
    created_at: datetime

class LatestPrediction(BaseModel):
    """Embedded latest prediction for vendor detail view."""
    prediction_id: int
    risk_label: str
    risk_score: float
    model_version: str
    predicted_at: str
    feature_payload: Optional[Dict[str, Any]] = None

class VendorDetailRead(BaseModel):
    """Full vendor detail with latest prediction."""
    id: int
    name: str
    gstin: Optional[str] = None
    pan: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    website: Optional[str] = None
    document_count: int = 0
    prediction_count: int = 0
    latest_prediction: Optional[LatestPrediction] = None
    created_at: datetime
    updated_at: datetime


# =====================================================================
#  Risk Prediction Request / Response (Module 5)
# =====================================================================
class RiskPredictionRequest(BaseModel):
    """Request body for POST /vendors/{id}/predict-risk.

    Features correspond to DataCo Supply Chain order attributes.
    Numeric and categorical values are both accepted.
    """
    features: Dict[str, Any] = Field(
        ...,
        description="Order/shipment features for late-delivery risk scoring.",
        examples=[{
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
        }],
    )

class RiskPredictionResponse(BaseModel):
    """Response from a risk prediction."""
    prediction_id: int
    vendor_id: int
    vendor_name: str
    risk_label: str
    risk_score: float
    probabilities: Dict[str, float]
    model_version: str
    predicted_at: str
    feature_values: Dict[str, Any]

class VendorRiskItem(BaseModel):
    """One vendor's risk status in the summary."""
    vendor_id: int
    vendor_name: str
    risk_label: str
    risk_score: Optional[float] = None
    predicted_at: Optional[str] = None

class RiskSummaryResponse(BaseModel):
    """Aggregate risk distribution."""
    total_vendors: int
    distribution: Dict[str, int]
    vendors: List[VendorRiskItem] = []


# =====================================================================
#  Analytics — Overview (Module 6)
# =====================================================================

class DocumentKPIs(BaseModel):
    """Document counts for the overview card."""
    total: int = 0
    completed: int = 0
    failed: int = 0
    pending: int = 0
    processing: int = 0

class VendorKPIs(BaseModel):
    """Vendor counts for the overview card."""
    total: int = 0
    with_risk_scores: int = 0
    unscored: int = 0

class EntityKPIs(BaseModel):
    """Entity counts for the overview card."""
    total: int = 0
    with_vendor_link: int = 0

class SpendKPIs(BaseModel):
    """Spend totals for the overview card."""
    total_amount: float = 0.0
    average_amount: float = 0.0
    documents_with_amount: int = 0

class AnalyticsOverviewResponse(BaseModel):
    """Top-level dashboard overview — all critical KPIs in one response."""
    generated_at: str
    documents: DocumentKPIs
    vendors: VendorKPIs
    entities: EntityKPIs
    risk_distribution: Dict[str, int]
    spend: SpendKPIs


# =====================================================================
#  Analytics — Document (Module 6)
# =====================================================================

class DailyUploadItem(BaseModel):
    """Single day in the upload timeline chart."""
    date: str
    count: int

class DocumentAnalyticsResponse(BaseModel):
    """Detailed document processing analytics."""
    total_documents: int = 0
    status_breakdown: Dict[str, int] = Field(default_factory=dict)
    ocr_success_rate: float = 0.0
    average_file_size_bytes: float = 0.0
    total_pages_processed: int = 0
    ocr_method_breakdown: Dict[str, int] = Field(default_factory=dict)
    mime_type_breakdown: Dict[str, int] = Field(default_factory=dict)
    daily_uploads: List[DailyUploadItem] = []
    latest_upload_at: Optional[str] = None


# =====================================================================
#  Analytics — Vendor (Module 6)
# =====================================================================

class ContactCompleteness(BaseModel):
    """How many vendors have contact details populated."""
    with_email: int = 0
    with_gstin: int = 0

class VendorAnalyticsResponse(BaseModel):
    """Vendor intelligence summary."""
    total_vendors: int = 0
    with_risk_scores: int = 0
    unscored: int = 0
    average_documents_per_vendor: float = 0.0
    max_documents_single_vendor: int = 0
    risk_breakdown: Dict[str, int] = Field(default_factory=dict)
    contact_completeness: ContactCompleteness = Field(default_factory=ContactCompleteness)
    latest_vendor_added_at: Optional[str] = None


# =====================================================================
#  Analytics — Risk Distribution (Module 6)
# =====================================================================

class ScoreBucket(BaseModel):
    """Single bucket in a risk-score histogram."""
    range: str
    count: int

class RiskDistributionResponse(BaseModel):
    """Risk label distribution and score histogram."""
    label_distribution: Dict[str, int] = Field(default_factory=dict)
    total_predictions: int = 0
    average_risk_score: Optional[float] = None
    score_buckets: List[ScoreBucket] = []
    model_versions: Dict[str, int] = Field(default_factory=dict)
    latest_prediction_at: Optional[str] = None


# =====================================================================
#  Analytics — Spend Summary (Module 6)
# =====================================================================

class SpendByType(BaseModel):
    """Spend grouped by entity type."""
    entity_type: str
    total_amount: float

class SpendByCurrency(BaseModel):
    """Spend grouped by currency."""
    currency: str
    total_amount: float

class SpendSummaryResponse(BaseModel):
    """Monetary spend analytics from extracted documents."""
    total_amount: float = 0.0
    average_amount: float = 0.0
    min_amount: float = 0.0
    max_amount: float = 0.0
    documents_with_amount: int = 0
    spend_by_entity_type: List[SpendByType] = []
    spend_by_currency: List[SpendByCurrency] = []


# =====================================================================
#  Analytics — Top Vendors (Module 6)
# =====================================================================

class TopVendorItem(BaseModel):
    """Single vendor in the top-vendors ranking."""
    rank: int
    vendor_id: int
    vendor_name: str
    total_value: float
    document_count: int = 0
    latest_risk_label: Optional[str] = None
    latest_risk_score: Optional[float] = None

class TopVendorsResponse(BaseModel):
    """Top vendors ranked by total procurement value."""
    top_vendors: List[TopVendorItem] = []
    total_vendors_with_spend: int = 0


# =====================================================================
#  Analytics — Extraction Summary (Module 6)
# =====================================================================

class ConfidenceBucket(BaseModel):
    """Single bucket in a confidence-score histogram."""
    range: str
    count: int

class ExtractionSummaryResponse(BaseModel):
    """Extraction quality and coverage analytics."""
    total_entities: int = 0
    total_documents: int = 0
    documents_with_extractions: int = 0
    documents_without_extractions: int = 0
    extraction_rate_percent: float = 0.0
    entity_type_breakdown: Dict[str, int] = Field(default_factory=dict)
    average_confidence_score: Optional[float] = None
    confidence_distribution: List[ConfidenceBucket] = []
    entities_with_vendor_link: int = 0
    vendor_link_rate_percent: float = 0.0
    field_coverage: Dict[str, int] = Field(default_factory=dict)

# =====================================================================
#  RAG — Request / Response (Module 7)
# =====================================================================

class RagAskRequest(BaseModel):
    """Request body for POST /rag/ask."""
    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Natural language question about the procurement documents.",
        examples=["What are the payment terms?"],
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of document chunks to retrieve.",
    )

class RagDocumentAskRequest(BaseModel):
    """Request body for POST /rag/ask-document/{document_id}."""
    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Question scoped to a specific document.",
        examples=["What is the total amount on this invoice?"],
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of chunks to retrieve from this document.",
    )

class RagSourceItem(BaseModel):
    """A single source chunk referenced in the answer."""
    document_id: int
    filename: str
    chunk_type: str
    relevance_score: float
    snippet: str

class RagAskResponse(BaseModel):
    """Response from a RAG question."""
    answer: str
    question: str
    grounded: bool = Field(
        description="True if the answer is based on retrieved document content.",
    )
    sources: List[RagSourceItem] = []
    documents_referenced: int = 0
    chunks_retrieved: int = 0
    chunks_searched: Optional[int] = None
    model: Optional[str] = None
    elapsed_seconds: Optional[float] = None

class RagIndexResponse(BaseModel):
    """Response from index building."""
    status: str
    message: str
    documents_indexed: int = 0
    chunks_created: int = 0
    embedding_model: Optional[str] = None
    embedding_dimension: Optional[int] = None
    index_path: Optional[str] = None
    elapsed_seconds: Optional[float] = None

class RagStatusResponse(BaseModel):
    """Current RAG index status."""
    index_exists: bool = False
    index_loaded: bool = False
    documents_indexed: int = 0
    chunks_indexed: int = 0
    embedding_model: str
    llm_model: str
    index_path: str
    created_at: Optional[str] = None

class RagIndexedDocumentItem(BaseModel):
    """Per-document stats in the index."""
    document_id: int
    filename: str
    chunk_count: int = 0
    total_chunk_length: int = 0

class RagIndexedDocumentsResponse(BaseModel):
    """List of documents in the vector index."""
    documents: List[RagIndexedDocumentItem] = []
    total: int = 0
    index_created_at: Optional[str] = None


# =====================================================================
#  Rebuild forward refs (DocumentRead ↔ ExtractedEntityRead, etc.)
# =====================================================================
DocumentRead.model_rebuild()
VendorRead.model_rebuild()


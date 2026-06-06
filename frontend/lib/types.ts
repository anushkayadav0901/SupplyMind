// frontend/lib/types.ts
// Shared TypeScript types for SupplyMind frontend.
// These mirror the Pydantic schemas in backend/app/schemas.py.

// ── API Error ──────────────────────────────────────────────────

export interface ApiError {
  detail: string;
  status?: number;
}

// ── Documents ──────────────────────────────────────────────────

export type OCRStatus = "pending" | "processing" | "completed" | "failed";

export interface Document {
  id: number;
  filename: string;
  original_filename: string;
  file_path: string;
  mime_type: string;
  file_size: number | null;
  page_count: number | null;
  extracted_text: string | null;
  ocr_status: OCRStatus;
  ocr_method: string | null;
  created_at: string;
  updated_at: string;
  extracted_entities: ExtractedEntity[];
}

export interface DocumentListItem {
  id: number;
  filename: string;
  original_filename: string;
  mime_type: string;
  file_size: number | null;
  page_count: number | null;
  ocr_status: OCRStatus;
  ocr_method: string | null;
  entity_count: number;
  created_at: string;
  updated_at: string;
}

export interface UploadResponse {
  success: boolean;
  message: string;
  document_id: number;
  entity_id: number | null;
  vendor_id: number | null;
  stored_filename: string;
  original_filename: string;
  mime_type: string;
  file_size: number | null;
  page_count: number | null;
  ocr_status: OCRStatus;
  ocr_method: string | null;
  text_length: number;
  extraction: {
    document_type: string | null;
    document_number: string | null;
    vendor_name: string | null;
    vendor_gstin: string | null;
    total_amount: number | null;
    currency: string | null;
    line_item_count: number;
    confidence_score: number;
  } | null;
  vendor: {
    id: number;
    name: string;
    gstin: string | null;
  } | null;
}

// ── Vendors ────────────────────────────────────────────────────

export interface Vendor {
  id: number;
  name: string;
  gstin: string | null;
  pan: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  address: string | null;
  website: string | null;
  created_at: string;
  updated_at: string;
}

export interface VendorListItem {
  id: number;
  name: string;
  gstin: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  latest_risk_label: string | null;
  latest_risk_score: number | null;
  prediction_count: number;
  document_count: number;
  created_at: string;
}

export interface VendorDetail {
  id: number;
  name: string;
  gstin: string | null;
  pan: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  address: string | null;
  website: string | null;
  document_count: number;
  prediction_count: number;
  latest_prediction: RiskPredictionSummary | null;
  created_at: string;
  updated_at: string;
}

// ── Extracted Entities ─────────────────────────────────────────

export interface ExtractedEntity {
  id: number;
  document_id: number;
  vendor_id: number | null;
  entity_type: string | null;
  entity_data: Record<string, unknown>;
  confidence_score: number | null;
  created_at: string;
}

// ── Risk Predictions ───────────────────────────────────────────

export type RiskLabel = "low" | "medium" | "high" | "critical";

export interface RiskPredictionSummary {
  prediction_id: number;
  risk_label: string;
  risk_score: number;
  model_version: string;
  predicted_at: string;
  feature_payload: Record<string, unknown> | null;
}

export interface RiskPredictionResponse {
  prediction_id: number;
  vendor_id: number;
  vendor_name: string;
  risk_label: string;
  risk_score: number;
  probabilities: Record<string, number>;
  model_version: string;
  predicted_at: string;
  feature_values: Record<string, unknown>;
}

export interface RiskSummary {
  total_vendors: number;
  distribution: Record<string, number>;
  vendors: VendorRiskItem[];
}

export interface VendorRiskItem {
  vendor_id: number;
  vendor_name: string;
  risk_label: string;
  risk_score: number | null;
  predicted_at: string | null;
}

// ── Analytics ──────────────────────────────────────────────────

export interface AnalyticsOverview {
  generated_at: string;
  documents: {
    total: number;
    completed: number;
    failed: number;
    pending: number;
    processing: number;
  };
  vendors: {
    total: number;
    with_risk_scores: number;
    unscored: number;
  };
  entities: {
    total: number;
    with_vendor_link: number;
  };
  risk_distribution: Record<string, number>;
  spend: {
    total_amount: number;
    average_amount: number;
    documents_with_amount: number;
  };
}

export interface DocumentAnalytics {
  total_documents: number;
  status_breakdown: Record<string, number>;
  ocr_success_rate: number;
  average_file_size_bytes: number;
  total_pages_processed: number;
  ocr_method_breakdown: Record<string, number>;
  mime_type_breakdown: Record<string, number>;
  daily_uploads: DailyUpload[];
  latest_upload_at: string | null;
}

export interface DailyUpload {
  date: string;
  count: number;
}

export interface VendorAnalytics {
  total_vendors: number;
  with_risk_scores: number;
  unscored: number;
  average_documents_per_vendor: number;
  max_documents_single_vendor: number;
  risk_breakdown: Record<string, number>;
  contact_completeness: {
    with_email: number;
    with_gstin: number;
  };
  latest_vendor_added_at: string | null;
}

export interface RiskDistribution {
  label_distribution: Record<string, number>;
  total_predictions: number;
  average_risk_score: number | null;
  score_buckets: ScoreBucket[];
  model_versions: Record<string, number>;
  latest_prediction_at: string | null;
}

export interface ScoreBucket {
  range: string;
  count: number;
}

export interface SpendSummary {
  total_amount: number;
  average_amount: number;
  min_amount: number;
  max_amount: number;
  documents_with_amount: number;
  spend_by_entity_type: SpendByType[];
  spend_by_currency: SpendByCurrency[];
}

export interface SpendByType {
  entity_type: string;
  total_amount: number;
}

export interface SpendByCurrency {
  currency: string;
  total_amount: number;
}

export interface TopVendorsResponse {
  top_vendors: TopVendorItem[];
  total_vendors_with_spend: number;
}

export interface TopVendorItem {
  rank: number;
  vendor_id: number;
  vendor_name: string;
  total_value: number;
  document_count: number;
  latest_risk_label: string | null;
  latest_risk_score: number | null;
}

export interface ExtractionSummary {
  total_entities: number;
  total_documents: number;
  documents_with_extractions: number;
  documents_without_extractions: number;
  extraction_rate_percent: number;
  entity_type_breakdown: Record<string, number>;
  average_confidence_score: number | null;
  confidence_distribution: ScoreBucket[];
  entities_with_vendor_link: number;
  vendor_link_rate_percent: number;
  field_coverage: Record<string, number>;
}

// ── RAG ────────────────────────────────────────────────────────

export interface RagSource {
  document_id: number;
  filename: string;
  chunk_type: string;
  relevance_score: number;
  snippet: string;
}

export interface RagAnswer {
  answer: string;
  question: string;
  grounded: boolean;
  sources: RagSource[];
  documents_referenced: number;
  chunks_retrieved: number;
  chunks_searched?: number | null;
  model: string | null;
  elapsed_seconds: number | null;
}

export interface RagIndexResponse {
  status: string;
  message: string;
  documents_indexed: number;
  chunks_created: number;
  embedding_model: string | null;
  embedding_dimension: number | null;
  index_path: string | null;
  elapsed_seconds: number | null;
}

export interface RagStatus {
  index_exists: boolean;
  index_loaded: boolean;
  documents_indexed: number;
  chunks_indexed: number;
  embedding_model: string;
  llm_model: string;
  index_path: string;
  created_at: string | null;
}

export interface RagIndexedDocument {
  document_id: number;
  filename: string;
  chunk_count: number;
  total_chunk_length: number;
}

export interface RagIndexedDocuments {
  documents: RagIndexedDocument[];
  total: number;
  index_created_at: string | null;
}

// ── Health ─────────────────────────────────────────────────────

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  database: string;
  timestamp: string;
}

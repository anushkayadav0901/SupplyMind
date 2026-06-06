import Link from "next/link";
import { AlertCircle, ArrowLeft, FileText } from "lucide-react";
import { RagQuestionPanel } from "@/components/rag/rag-question-panel";
import { StatusBadge } from "@/components/status-badge";
import { api } from "@/lib/api";
import { formatBytes, formatDate, formatNumber, formatPercent, titleCase } from "@/lib/format";
import type { Document, VendorDetail } from "@/lib/types";

interface DocumentDetailData {
  document: Document | null;
  vendor: VendorDetail | null;
  error: string | null;
}

async function getDocumentDetail(id: number): Promise<DocumentDetailData> {
  try {
    const document = await api.getDocumentById(id);
    const vendorId = document.extracted_entities.find((entity) => entity.vendor_id)?.vendor_id;
    const vendor = vendorId ? await api.getVendorById(vendorId).catch(() => null) : null;

    return { document, vendor, error: null };
  } catch (error) {
    return {
      document: null,
      vendor: null,
      error: error instanceof Error ? error.message : "Document detail could not be loaded.",
    };
  }
}

export default async function DocumentDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const documentId = Number(id);
  const { document, vendor, error } = await getDocumentDetail(documentId);
  const textPreview = document?.extracted_text?.trim()
    ? document.extracted_text.trim().slice(0, 1200)
    : "No extracted text is available for this document yet.";

  return (
    <div className="space-y-8">
      <div>
        <Link href="/documents" className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="size-4" />
          Back to documents
        </Link>
        <div className="mt-4 flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
          <div>
            <h1 className="text-2xl font-semibold text-foreground">
              {document?.original_filename ?? "Document detail"}
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              OCR output, extracted procurement entities, linked vendor, and document Q&A.
            </p>
          </div>
          {document ? <StatusBadge value={document.ocr_status} /> : null}
        </div>
      </div>

      {error ? (
        <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          <AlertCircle className="size-4" />
          {error}
        </div>
      ) : null}

      {document ? (
        <>
          <section className="grid gap-4 md:grid-cols-4">
            <Detail label="File Size" value={formatBytes(document.file_size)} />
            <Detail label="Pages" value={formatNumber(document.page_count)} />
            <Detail label="OCR Method" value={titleCase(document.ocr_method)} />
            <Detail label="Uploaded" value={formatDate(document.created_at)} />
          </section>

          <section className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
            <div className="rounded-lg border border-border bg-card p-5">
              <div className="flex items-center gap-2">
                <FileText className="size-4 text-muted-foreground" />
                <h2 className="text-base font-semibold">Extracted Text Summary</h2>
              </div>
              <p className="mt-4 whitespace-pre-wrap text-sm leading-6 text-muted-foreground">
                {textPreview}
                {document.extracted_text && document.extracted_text.length > 1200 ? "..." : ""}
              </p>
            </div>

            <div className="rounded-lg border border-border bg-card p-5">
              <h2 className="text-base font-semibold">Vendor and Risk</h2>
              {vendor ? (
                <div className="mt-4 space-y-4">
                  <Detail label="Vendor" value={vendor.name} compact />
                  <Detail label="GSTIN" value={vendor.gstin ?? "Not available"} compact />
                  <Detail label="Documents" value={formatNumber(vendor.document_count)} compact />
                  <Detail label="Predictions" value={formatNumber(vendor.prediction_count)} compact />
                  <div className="flex items-center justify-between gap-4 border-t border-border pt-4">
                    <span className="text-sm text-muted-foreground">Latest Risk</span>
                    <div className="flex items-center gap-2">
                      <StatusBadge value={vendor.latest_prediction?.risk_label ?? "unscored"} />
                      {vendor.latest_prediction?.risk_score != null ? (
                        <span className="text-sm font-medium">
                          {formatPercent(vendor.latest_prediction.risk_score)}
                        </span>
                      ) : null}
                    </div>
                  </div>
                </div>
              ) : (
                <p className="mt-4 text-sm text-muted-foreground">
                  No linked vendor was found in the extracted entities.
                </p>
              )}
            </div>
          </section>

          <section className="rounded-lg border border-border bg-card">
            <div className="border-b border-border p-5">
              <h2 className="text-base font-semibold">Structured Entities</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                {formatNumber(document.extracted_entities.length)} extracted records linked to this document.
              </p>
            </div>
            <div className="divide-y divide-border">
              {document.extracted_entities.length > 0 ? (
                document.extracted_entities.map((entity) => (
                  <div key={entity.id} className="p-5">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <p className="text-sm font-medium">{titleCase(entity.entity_type)}</p>
                        <p className="mt-1 text-xs text-muted-foreground">
                          Confidence {entity.confidence_score != null ? formatPercent(entity.confidence_score) : "Not available"}
                        </p>
                      </div>
                      {entity.vendor_id ? <span className="text-xs text-muted-foreground">Vendor #{entity.vendor_id}</span> : null}
                    </div>
                    <pre className="mt-3 overflow-x-auto rounded-md border border-border bg-muted/30 p-3 text-xs leading-5 text-muted-foreground">
                      {JSON.stringify(entity.entity_data, null, 2)}
                    </pre>
                  </div>
                ))
              ) : (
                <p className="p-5 text-sm text-muted-foreground">No structured entities are available yet.</p>
              )}
            </div>
          </section>

          <section>
            <div className="mb-3">
              <h2 className="text-base font-semibold">Ask About This Document</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Questions are scoped to this document when the RAG index is available.
              </p>
            </div>
            <RagQuestionPanel documentId={document.id} />
          </section>
        </>
      ) : null}
    </div>
  );
}

function Detail({ label, value, compact = false }: { label: string; value: string; compact?: boolean }) {
  return (
    <div className={compact ? "flex items-center justify-between gap-4" : "rounded-lg border border-border bg-card p-4"}>
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className={compact ? "text-sm font-medium text-right" : "mt-2 text-lg font-semibold"}>{value}</p>
    </div>
  );
}

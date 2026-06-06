import Link from "next/link";
import { AlertCircle, FileText } from "lucide-react";
import { EmptyState } from "@/components/empty-state";
import { StatusBadge } from "@/components/status-badge";
import { UploadDocumentButton } from "@/components/documents/upload-document-button";
import { api } from "@/lib/api";
import { formatBytes, formatDate, formatNumber, titleCase } from "@/lib/format";
import type { DocumentListItem } from "@/lib/types";

async function getDocuments(): Promise<{ documents: DocumentListItem[]; error: string | null }> {
  try {
    return { documents: await api.listDocuments(0, 100), error: null };
  } catch (error) {
    return {
      documents: [],
      error: error instanceof Error ? error.message : "Documents could not be loaded.",
    };
  }
}

export default async function DocumentsPage() {
  const { documents, error } = await getDocuments();
  const completed = documents.filter((document) => document.ocr_status === "completed").length;
  const processing = documents.filter((document) => document.ocr_status === "processing").length;
  const failed = documents.filter((document) => document.ocr_status === "failed").length;

  return (
    <div className="space-y-8">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">Documents</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Uploaded procurement files, OCR status, extracted entities, and processing metadata.
          </p>
        </div>
        <UploadDocumentButton />
      </div>

      {error ? (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          <div className="flex items-start gap-3">
            <AlertCircle className="mt-0.5 size-4 shrink-0" />
            <div>
              <p className="font-medium">Backend connection needs attention</p>
              <p className="mt-1 leading-6 text-amber-800">{error}</p>
            </div>
          </div>
        </div>
      ) : null}

      <section className="grid gap-4 md:grid-cols-4">
        <Stat label="Total" value={formatNumber(documents.length)} />
        <Stat label="Completed" value={formatNumber(completed)} />
        <Stat label="Processing" value={formatNumber(processing)} />
        <Stat label="Failed" value={formatNumber(failed)} />
      </section>

      <section className="rounded-lg border border-border bg-card">
        <div className="flex flex-col gap-3 border-b border-border p-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-base font-semibold">Document Register</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              {documents.length > 0
                ? `${formatNumber(documents.length)} files available for review.`
                : "Uploaded files will appear here with OCR status, entities, and timestamps."}
            </p>
          </div>
        </div>

        {documents.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[860px] text-left text-sm">
              <thead className="border-b border-border bg-muted/40 text-xs uppercase text-muted-foreground">
                <tr>
                  <th className="px-4 py-3 font-medium">Document</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">OCR Method</th>
                  <th className="px-4 py-3 font-medium">Entities</th>
                  <th className="px-4 py-3 font-medium">Size</th>
                  <th className="px-4 py-3 font-medium">Uploaded</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {documents.map((document) => (
                  <tr key={document.id} className="hover:bg-muted/30">
                    <td className="px-4 py-3">
                      <Link href={`/documents/${document.id}`} className="font-medium text-foreground hover:text-primary">
                        {document.original_filename}
                      </Link>
                      <p className="mt-1 text-xs text-muted-foreground">{document.mime_type}</p>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge value={document.ocr_status} />
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">{titleCase(document.ocr_method)}</td>
                    <td className="px-4 py-3">{formatNumber(document.entity_count)}</td>
                    <td className="px-4 py-3 text-muted-foreground">{formatBytes(document.file_size)}</td>
                    <td className="px-4 py-3 text-muted-foreground">{formatDate(document.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-5">
            <EmptyState
              icon={FileText}
              title={error ? "Document data is temporarily unavailable" : "No documents uploaded yet"}
              framed={false}
              description={
                error
                  ? "The frontend is ready, but the backend could not be reached. Start the FastAPI server and refresh to load document data."
                  : "Upload a procurement document to start OCR, entity extraction, vendor linking, and risk analysis."
              }
            />
          </div>
        )}
      </section>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="mt-2 text-2xl font-semibold">{value}</p>
    </div>
  );
}

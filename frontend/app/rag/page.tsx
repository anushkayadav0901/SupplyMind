import type React from "react";
import { AlertCircle, Database, FileText, Server } from "lucide-react";
import { EmptyState } from "@/components/empty-state";
import { IndexDocumentsButton } from "@/components/rag/index-documents-button";
import { RagQuestionPanel } from "@/components/rag/rag-question-panel";
import { StatusBadge } from "@/components/status-badge";
import { api } from "@/lib/api";
import { formatDate, formatNumber } from "@/lib/format";
import type { RagIndexedDocuments, RagStatus } from "@/lib/types";

async function getRagData(): Promise<{
  status: RagStatus | null;
  indexed: RagIndexedDocuments | null;
  error: string | null;
}> {
  const [statusResult, indexedResult] = await Promise.allSettled([
    api.getRagStatus(),
    api.getRagIndexedDocuments(),
  ] as const);
  const messages = [statusResult, indexedResult]
    .filter((result) => result.status === "rejected")
    .map((result) => result.reason)
    .map((reason) => (reason instanceof Error ? reason.message : "RAG status could not be loaded."));

  return {
    status: statusResult.status === "fulfilled" ? statusResult.value : null,
    indexed: indexedResult.status === "fulfilled" ? indexedResult.value : null,
    error: messages.length > 0 ? [...new Set(messages)].join(" ") : null,
  };
}

export default async function RagPage() {
  const { status, indexed, error } = await getRagData();
  const statusValue = status?.index_exists && status.index_loaded ? "indexed" : "offline";

  return (
    <div className="space-y-8">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">RAG Assistant</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Ask grounded questions across indexed procurement documents and inspect retrieved sources.
          </p>
        </div>
        <IndexDocumentsButton />
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
        <StatusCard label="Index" value={statusValue} detail={status?.index_path ?? "No index path"} icon={Database} />
        <StatusCard label="Documents" value={formatNumber(status?.documents_indexed)} detail="Indexed documents" icon={FileText} />
        <StatusCard label="Chunks" value={formatNumber(status?.chunks_indexed)} detail="Searchable chunks" icon={Server} />
        <StatusCard label="Created" value={formatDate(status?.created_at)} detail={status?.embedding_model ?? "Embedding model"} icon={Database} />
      </section>

      <section>
        <RagQuestionPanel />
      </section>

      <section className="rounded-lg border border-border bg-card">
        <div className="flex flex-col gap-3 border-b border-border p-5 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-base font-semibold">Indexed Sources</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              {formatNumber(indexed?.total)} documents currently available to the assistant.
            </p>
          </div>
          <StatusBadge value={statusValue} />
        </div>
        <div className="divide-y divide-border">
          {(indexed?.documents ?? []).length > 0 ? (
            indexed?.documents.map((document) => (
              <div key={document.document_id} className="flex flex-col gap-3 p-5 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm font-medium">{document.filename}</p>
                  <p className="mt-1 text-xs text-muted-foreground">Document #{document.document_id}</p>
                </div>
                <div className="flex gap-6 text-sm">
                  <div>
                    <p className="text-xs text-muted-foreground">Chunks</p>
                    <p className="mt-1 font-medium">{formatNumber(document.chunk_count)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Characters</p>
                    <p className="mt-1 font-medium">{formatNumber(document.total_chunk_length)}</p>
                  </div>
                </div>
              </div>
            ))
          ) : (
            <div className="p-5">
              <EmptyState
                icon={Database}
                title={error ? "RAG index is temporarily unavailable" : "No indexed documents yet"}
                description={
                  error
                    ? "The assistant interface is ready, but the backend could not be reached. Start FastAPI and refresh to load index status."
                    : "Build the RAG index after OCR text exists, then indexed document sources will appear here."
                }
                framed={false}
              />
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

function StatusCard({
  label,
  value,
  detail,
  icon: Icon,
}: {
  label: string;
  value: string;
  detail: string;
  icon: React.ComponentType<{ className?: string }>;
}) {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm text-muted-foreground">{label}</p>
        <Icon className="size-4 text-muted-foreground" />
      </div>
      <div className="mt-3">
        {label === "Index" ? <StatusBadge value={value} /> : <p className="text-lg font-semibold">{value}</p>}
      </div>
      <p className="mt-2 truncate text-xs text-muted-foreground">{detail}</p>
    </div>
  );
}

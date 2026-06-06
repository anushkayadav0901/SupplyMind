import type React from "react";
import { AlertCircle, Boxes, FileText, IndianRupee, ShieldCheck, Users } from "lucide-react";
import { EmptyState } from "@/components/empty-state";
import { StatusBadge } from "@/components/status-badge";
import { api } from "@/lib/api";
import { formatCurrency, formatDate, formatNumber, titleCase } from "@/lib/format";
import type { AnalyticsOverview, DocumentListItem, VendorListItem } from "@/lib/types";

interface DashboardData {
  overview: AnalyticsOverview | null;
  documents: DocumentListItem[];
  vendors: VendorListItem[];
  error: string | null;
}

async function getDashboardData(): Promise<DashboardData> {
  try {
    const [overview, documents, vendors] = await Promise.all([
      api.getOverviewAnalytics(),
      api.listDocuments(0, 5),
      api.listVendors(0, 5),
    ]);

    return { overview, documents, vendors, error: null };
  } catch (error) {
    return {
      overview: null,
      documents: [],
      vendors: [],
      error: error instanceof Error ? error.message : "Dashboard data could not be loaded.",
    };
  }
}

export default async function DashboardPage() {
  const { overview, documents, vendors, error } = await getDashboardData();
  const highRiskCount =
    (overview?.risk_distribution.high ?? 0) + (overview?.risk_distribution.critical ?? 0);
  const completedDocuments = overview?.documents.completed ?? 0;
  const totalDocuments = overview?.documents.total ?? 0;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Dashboard</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Procurement overview, document processing, vendor coverage, and risk signals.
        </p>
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

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Documents"
          value={formatNumber(totalDocuments)}
          detail={`${formatNumber(completedDocuments)} completed`}
          icon={FileText}
        />
        <MetricCard
          label="Vendors"
          value={formatNumber(overview?.vendors.total)}
          detail={`${formatNumber(overview?.vendors.with_risk_scores)} risk scored`}
          icon={Users}
        />
        <MetricCard
          label="Elevated Risk"
          value={formatNumber(highRiskCount)}
          detail="High and critical vendors"
          icon={ShieldCheck}
        />
        <MetricCard
          label="Spend"
          value={formatCurrency(overview?.spend.total_amount)}
          detail={`${formatNumber(overview?.spend.documents_with_amount)} documents with value`}
          icon={IndianRupee}
        />
      </section>

      <section className="grid gap-6 lg:grid-cols-[1.25fr_0.75fr]">
        <div className="rounded-lg border border-border bg-card p-5">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="text-base font-semibold">Recent Activity</h2>
              <p className="mt-1 text-sm text-muted-foreground">Latest uploaded procurement documents.</p>
            </div>
            <Boxes className="size-5 text-muted-foreground" />
          </div>
          <div className="mt-5 divide-y divide-border">
            {documents.length > 0 ? (
              documents.map((document) => (
                <div key={document.id} className="flex items-center justify-between gap-4 py-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">{document.original_filename}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {formatDate(document.created_at)} - {document.entity_count} entities
                    </p>
                  </div>
                  <StatusBadge value={document.ocr_status} />
                </div>
              ))
            ) : (
              <EmptyState
                icon={FileText}
                title={error ? "Activity is temporarily unavailable" : "No recent documents yet"}
                description={
                  error
                    ? "Start the FastAPI backend and refresh to load the latest procurement activity."
                    : "Uploaded documents will appear here as OCR and entity extraction complete."
                }
                framed={false}
                action={error ? undefined : { label: "Open documents", href: "/documents" }}
              />
            )}
          </div>
        </div>

        <div className="rounded-lg border border-border bg-card p-5">
          <h2 className="text-base font-semibold">Procurement Summary</h2>
          <div className="mt-5 space-y-4">
            <SummaryRow label="Processing Queue" value={formatNumber((overview?.documents.pending ?? 0) + (overview?.documents.processing ?? 0))} />
            <SummaryRow label="Linked Entities" value={formatNumber(overview?.entities.with_vendor_link)} />
            <SummaryRow label="Average Spend" value={formatCurrency(overview?.spend.average_amount)} />
            <SummaryRow label="Generated" value={formatDate(overview?.generated_at)} />
          </div>
          <div className="mt-6">
            <h3 className="text-sm font-medium">Vendor Watchlist</h3>
            <div className="mt-3 space-y-2">
              {vendors.length > 0 ? (
                vendors.slice(0, 3).map((vendor) => (
                  <div key={vendor.id} className="flex items-center justify-between gap-3 rounded-md border border-border px-3 py-2">
                    <span className="truncate text-sm">{vendor.name}</span>
                    <StatusBadge value={vendor.latest_risk_label ?? "unscored"} />
                  </div>
                ))
              ) : (
                <div className="rounded-md bg-muted/40 px-3 py-4 text-sm leading-6 text-muted-foreground">
                  {error
                    ? "Vendor watchlist will load once the backend is reachable."
                    : "Vendor watchlist will populate after extracted suppliers receive risk scores."}
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      <section className="rounded-lg border border-border bg-card p-5">
        <h2 className="text-base font-semibold">Risk Distribution</h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {["low", "medium", "high", "critical"].map((label) => (
            <div key={label} className="rounded-md border border-border p-4">
              <StatusBadge value={label} />
              <p className="mt-3 text-2xl font-semibold">
                {formatNumber(overview?.risk_distribution[label] ?? 0)}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">{titleCase(label)} risk vendors</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function MetricCard({
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
    <div className="rounded-lg border border-border bg-card p-5">
      <div className="flex items-center justify-between gap-4">
        <p className="text-sm font-medium text-muted-foreground">{label}</p>
        <Icon className="size-4 text-muted-foreground" />
      </div>
      <p className="mt-4 text-2xl font-semibold">{value}</p>
      <p className="mt-1 text-sm text-muted-foreground">{detail}</p>
    </div>
  );
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-border pb-3 last:border-b-0">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="text-sm font-medium">{value}</span>
    </div>
  );
}

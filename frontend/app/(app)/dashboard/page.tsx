import type React from "react";
import { AlertCircle, Boxes, Circle, FileText, IndianRupee, ShieldCheck, Users } from "lucide-react";
import { EmptyState } from "@/components/empty-state";
import { StatusBadge } from "@/components/status-badge";
import { api } from "@/lib/api";
import { formatCurrency, formatDate, formatNumber, titleCase } from "@/lib/format";
import type { AnalyticsOverview, DocumentListItem, VendorListItem } from "@/lib/types";
import { cn } from "@/lib/utils";

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

const riskBorderColor: Record<string, string> = {
  low: "border-l-emerald-400",
  medium: "border-l-amber-400",
  high: "border-l-orange-400",
  critical: "border-l-red-400",
};

const riskDescription: Record<string, string> = {
  low: "Within acceptable thresholds",
  medium: "Requires periodic monitoring",
  high: "Needs active mitigation",
  critical: "Immediate attention required",
};

export default async function DashboardPage() {
  const { overview, documents, vendors, error } = await getDashboardData();
  const highRiskCount =
    (overview?.risk_distribution.high ?? 0) + (overview?.risk_distribution.critical ?? 0);
  const completedDocuments = overview?.documents.completed ?? 0;
  const totalDocuments = overview?.documents.total ?? 0;

  return (
    <div className="space-y-10">
      {/* ─── Page Header ─── */}
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Dashboard</h1>
        <p className="mt-1.5 text-[15px] leading-relaxed text-muted-foreground">
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

      {/* ─── Section: OVERVIEW ─── */}
      <div className="space-y-4">
        <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground/70">
          Overview
        </p>
        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <MetricCard
            label="Documents"
            value={formatNumber(totalDocuments)}
            detail={`${formatNumber(completedDocuments)} completed`}
            icon={FileText}
            accent
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
      </div>

      {/* ─── Section: INTELLIGENCE ─── */}
      <div className="space-y-4">
        <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground/70">
          Intelligence
        </p>
        <section className="grid gap-6 lg:grid-cols-[1.25fr_0.75fr]">
          {/* Recent Activity */}
          <div className="rounded-lg border border-border bg-card p-5">
            <div className="flex items-center justify-between gap-4">
              <div>
                <h2 className="text-base font-semibold text-foreground">Recent Activity</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  Latest uploaded procurement documents.
                </p>
              </div>
              <div className="flex size-9 items-center justify-center rounded-full bg-muted/50">
                <Boxes className="size-4 text-muted-foreground" />
              </div>
            </div>
            <div className="mt-5">
              {documents.length > 0 ? (
                <div className="space-y-1">
                  {documents.map((document) => (
                    <div
                      key={document.id}
                      className="group flex items-center justify-between gap-4 rounded-md px-3 py-3 transition-colors hover:bg-muted/40"
                    >
                      <div className="flex min-w-0 items-start gap-3">
                        <div className="mt-1 flex size-5 shrink-0 items-center justify-center rounded bg-slate-100">
                          <FileText className="size-3 text-slate-500" />
                        </div>
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium text-foreground">
                            {document.original_filename}
                          </p>
                          <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                            <span>{formatDate(document.created_at)}</span>
                            <span className="text-border">·</span>
                            <span className="inline-flex items-center rounded bg-slate-100 px-1.5 py-0.5 text-[11px] font-medium text-slate-600">
                              {document.entity_count} entities
                            </span>
                          </div>
                        </div>
                      </div>
                      <StatusBadge value={document.ocr_status} />
                    </div>
                  ))}
                </div>
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

          {/* Procurement Summary + Vendor Watchlist */}
          <div className="rounded-lg border border-border bg-card p-5">
            {/* Procurement Summary */}
            <div>
              <h2 className="text-base font-semibold text-foreground">Procurement Summary</h2>
              <p className="mt-1 text-sm text-muted-foreground">Key processing metrics</p>
              <div className="mt-5 space-y-4">
                <SummaryRow
                  label="Processing Queue"
                  value={formatNumber(
                    (overview?.documents.pending ?? 0) + (overview?.documents.processing ?? 0)
                  )}
                />
                <SummaryRow
                  label="Linked Entities"
                  value={formatNumber(overview?.entities.with_vendor_link)}
                />
                <SummaryRow
                  label="Average Spend"
                  value={formatCurrency(overview?.spend.average_amount)}
                />
                <SummaryRow label="Generated" value={formatDate(overview?.generated_at)} />
              </div>
            </div>

            {/* Divider */}
            <div className="my-6 border-t border-dashed border-border" />

            {/* Vendor Watchlist */}
            <div>
              <h3 className="text-sm font-semibold text-foreground">Vendor Watchlist</h3>
              <p className="mt-0.5 text-xs text-muted-foreground">Top vendors by risk priority</p>
              <div className="mt-3 space-y-2">
                {vendors.length > 0 ? (
                  vendors.slice(0, 3).map((vendor) => (
                    <div
                      key={vendor.id}
                      className="flex items-center justify-between gap-3 rounded-lg border border-border bg-muted/20 px-3 py-2.5 transition-colors hover:bg-muted/40"
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="flex size-7 shrink-0 items-center justify-center rounded-full bg-indigo-50 text-xs font-semibold text-indigo-600">
                          {vendor.name?.charAt(0)?.toUpperCase() ?? "?"}
                        </div>
                        <span className="truncate text-sm font-medium text-foreground">
                          {vendor.name}
                        </span>
                      </div>
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
      </div>

      {/* ─── Section: RISK ─── */}
      <div className="space-y-4">
        <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground/70">
          Risk
        </p>
        <section className="rounded-lg border border-border bg-card p-5">
          <h2 className="text-base font-semibold text-foreground">Risk Distribution</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Vendor risk breakdown across severity levels
          </p>
          <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {["low", "medium", "high", "critical"].map((label) => (
              <div
                key={label}
                className={cn(
                  "rounded-md border border-border border-l-[3px] p-4",
                  riskBorderColor[label]
                )}
              >
                <StatusBadge value={label} />
                <p className="mt-3 text-3xl font-semibold tracking-tight text-foreground">
                  {formatNumber(overview?.risk_distribution[label] ?? 0)}
                </p>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  {titleCase(label)} risk vendors
                </p>
                <p className="mt-1.5 text-[11px] leading-snug text-muted-foreground/70">
                  {riskDescription[label]}
                </p>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

/* ─── Helper Components ─── */

function MetricCard({
  label,
  value,
  detail,
  icon: Icon,
  accent = false,
}: {
  label: string;
  value: string;
  detail: string;
  icon: React.ComponentType<{ className?: string }>;
  accent?: boolean;
}) {
  return (
    <div
      className={cn(
        "rounded-lg border border-border bg-card p-5",
        accent && "border-l-[3px] border-l-indigo-500"
      )}
    >
      <div className="flex items-center justify-between gap-4">
        <p className="text-sm font-medium text-muted-foreground">{label}</p>
        <div className="flex size-8 items-center justify-center rounded-full bg-muted/60">
          <Icon className="size-4 text-muted-foreground" />
        </div>
      </div>
      <p className="mt-3 text-3xl font-semibold tracking-tight text-foreground">{value}</p>
      <p className="mt-1 text-sm text-muted-foreground">{detail}</p>
    </div>
  );
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-border pb-3 last:border-b-0">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="text-sm font-semibold text-foreground">{value}</span>
    </div>
  );
}

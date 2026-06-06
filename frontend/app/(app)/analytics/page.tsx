import type React from "react";
import {
  AlertCircle,
  BarChart3,
  DollarSign,
  FileText,
  Layers,
  PieChart,
  ShieldCheck,
  TrendingUp,
} from "lucide-react";
import { EmptyState } from "@/components/empty-state";
import { StatusBadge } from "@/components/status-badge";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { formatBytes, formatCurrency, formatDate, formatNumber, titleCase } from "@/lib/format";
import type {
  DocumentAnalytics,
  ExtractionSummary,
  RiskDistribution,
  SpendSummary,
  TopVendorsResponse,
  VendorAnalytics,
} from "@/lib/types";

interface AnalyticsData {
  documents: DocumentAnalytics | null;
  vendors: VendorAnalytics | null;
  risk: RiskDistribution | null;
  spend: SpendSummary | null;
  topVendors: TopVendorsResponse | null;
  extraction: ExtractionSummary | null;
  error: string | null;
}

async function getAnalyticsData(): Promise<AnalyticsData> {
  const [documents, vendors, risk, spend, topVendors, extraction] = await Promise.allSettled([
    api.getDocumentAnalytics(),
    api.getVendorAnalytics(),
    api.getRiskDistribution(),
    api.getSpendSummary(),
    api.getTopVendors(8),
    api.getExtractionSummary(),
  ] as const);

  return {
    documents: documents.status === "fulfilled" ? documents.value : null,
    vendors: vendors.status === "fulfilled" ? vendors.value : null,
    risk: risk.status === "fulfilled" ? risk.value : null,
    spend: spend.status === "fulfilled" ? spend.value : null,
    topVendors: topVendors.status === "fulfilled" ? topVendors.value : null,
    extraction: extraction.status === "fulfilled" ? extraction.value : null,
    error: getSettledError([documents, vendors, risk, spend, topVendors, extraction]),
  };
}

export default async function AnalyticsPage() {
  const data = await getAnalyticsData();

  return (
    <div className="space-y-10">
      {/* ── Page header ── */}
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Analytics</h1>
        <p className="mt-1 text-sm leading-6 text-muted-foreground">
          Processing health, extraction quality, spend signals, vendor concentration, and risk
          distribution.
        </p>
      </div>

      {data.error ? (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          <div className="flex items-start gap-3">
            <AlertCircle className="mt-0.5 size-4 shrink-0" />
            <div>
              <p className="font-medium">Backend connection needs attention</p>
              <p className="mt-1 leading-6 text-amber-800">{data.error}</p>
            </div>
          </div>
        </div>
      ) : null}

      {/* ── Key Metrics ── */}
      <section>
        <SectionLabel>Key Metrics</SectionLabel>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Metric
            label="OCR Success"
            value={formatMetricPercent(data.documents?.ocr_success_rate)}
            icon={FileText}
            accent="indigo"
          />
          <Metric
            label="Average Risk"
            value={formatMetricPercent((data.risk?.average_risk_score ?? 0) * 100)}
            icon={ShieldCheck}
            accent="emerald"
          />
          <Metric
            label="Total Spend"
            value={formatCurrency(data.spend?.total_amount)}
            icon={DollarSign}
            accent="amber"
          />
          <Metric
            label="Extraction Rate"
            value={formatMetricPercent(data.extraction?.extraction_rate_percent)}
            icon={Layers}
            accent="violet"
          />
        </div>
      </section>

      {/* ── Risk & Processing ── */}
      <section>
        <SectionLabel>Risk &amp; Processing</SectionLabel>
        <div className="grid gap-6 lg:grid-cols-2">
          <Panel title="Risk Distribution" description="Latest prediction labels across vendors." icon={PieChart} accentColor="emerald">
            <div className="space-y-5">
              {Object.entries(data.risk?.label_distribution ?? {}).length > 0 ? (
                Object.entries(data.risk?.label_distribution ?? {}).map(([label, count]) => (
                  <BarRow key={label} label={label} value={count} max={data.risk?.total_predictions ?? 1} />
                ))
              ) : (
                <EmptyState
                  icon={PieChart}
                  title="No risk predictions yet"
                  description="Risk distribution will appear after vendors receive ML predictions from extracted procurement data."
                  framed={false}
                />
              )}
            </div>
          </Panel>

          <Panel title="Document Processing" description="Status and OCR method coverage." icon={FileText} accentColor="indigo">
            <div className="grid gap-3 sm:grid-cols-2">
              <DetailCard label="Total Documents" value={formatNumber(data.documents?.total_documents)} />
              <DetailCard label="Pages Processed" value={formatNumber(data.documents?.total_pages_processed)} />
              <DetailCard label="Average File Size" value={formatBytes(data.documents?.average_file_size_bytes)} />
              <DetailCard label="Latest Upload" value={formatDate(data.documents?.latest_upload_at)} />
            </div>
            {Object.entries(data.documents?.status_breakdown ?? {}).length > 0 ? (
              <div className="mt-5 space-y-2.5">
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Status Breakdown</p>
                {Object.entries(data.documents?.status_breakdown ?? {}).map(([status, count]) => (
                  <div key={status} className="flex items-center justify-between gap-4 rounded-md px-3 py-2 bg-muted/30">
                    <div className="flex items-center gap-2.5">
                      <StatusDot status={status} />
                      <StatusBadge value={status} />
                    </div>
                    <span className="text-sm font-semibold tabular-nums">{formatNumber(count)}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="mt-5 text-sm leading-6 text-muted-foreground">
                Processing status breakdown will appear once documents are uploaded.
              </p>
            )}
          </Panel>
        </div>
      </section>

      {/* ── Vendors & Extraction ── */}
      <section>
        <SectionLabel>Vendors &amp; Extraction</SectionLabel>
        <div className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
          <Panel title="Top Vendors" description="Vendors ranked by extracted procurement value." icon={TrendingUp} accentColor="amber">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[640px] text-left text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="pb-3 pr-3 text-xs font-medium uppercase tracking-wide text-muted-foreground w-14">Rank</th>
                    <th className="pb-3 pr-3 text-xs font-medium uppercase tracking-wide text-muted-foreground">Vendor</th>
                    <th className="pb-3 pr-3 text-xs font-medium uppercase tracking-wide text-muted-foreground text-right">Spend</th>
                    <th className="pb-3 pr-3 text-xs font-medium uppercase tracking-wide text-muted-foreground text-center">Risk</th>
                    <th className="pb-3 text-xs font-medium uppercase tracking-wide text-muted-foreground text-right">Docs</th>
                  </tr>
                </thead>
                <tbody>
                  {(data.topVendors?.top_vendors ?? []).length > 0 ? (
                    data.topVendors?.top_vendors.map((vendor, idx) => (
                      <tr
                        key={`${vendor.rank}-${vendor.vendor_id}`}
                        className={cn(
                          "border-b border-border/50 last:border-0 transition-colors",
                          idx % 2 === 1 && "bg-muted/20"
                        )}
                      >
                        <td className="py-3.5 pr-3">
                          <RankBadge rank={vendor.rank} />
                        </td>
                        <td className="py-3.5 pr-3 font-medium text-foreground">{vendor.vendor_name}</td>
                        <td className="py-3.5 pr-3 text-right tabular-nums">{formatCurrency(vendor.total_value)}</td>
                        <td className="py-3.5 pr-3 text-center">
                          <StatusBadge value={vendor.latest_risk_label ?? "unscored"} />
                        </td>
                        <td className="py-3.5 text-right tabular-nums text-muted-foreground">{formatNumber(vendor.document_count)}</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={5} className="py-10 text-center text-sm text-muted-foreground">
                        Spend-linked vendors will appear after extracted amounts are associated with suppliers.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </Panel>

          <Panel title="Extraction Summary" description="Entity quality and field coverage." icon={BarChart3} accentColor="violet">
            <div className="grid gap-3 sm:grid-cols-2">
              <DetailCard label="Entities" value={formatNumber(data.extraction?.total_entities)} />
              <DetailCard label="Docs With Extractions" value={formatNumber(data.extraction?.documents_with_extractions)} />
              <DetailCard label="Vendor Link Rate" value={formatMetricPercent(data.extraction?.vendor_link_rate_percent)} />
              <DetailCard
                label="Average Confidence"
                value={data.extraction?.average_confidence_score != null ? formatMetricPercent(data.extraction.average_confidence_score * 100) : "Not available"}
              />
            </div>
            <div className="mt-5">
              {Object.entries(data.extraction?.entity_type_breakdown ?? {}).length > 0 ? (
                <div className="space-y-2.5">
                  <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Entity Types</p>
                  {(() => {
                    const entries = Object.entries(data.extraction?.entity_type_breakdown ?? {});
                    const maxCount = Math.max(...entries.map(([, c]) => c), 1);
                    return entries.map(([entityType, count]) => (
                      <EntityTypeRow key={entityType} entityType={entityType} count={count} maxCount={maxCount} />
                    ));
                  })()}
                </div>
              ) : (
                <p className="text-sm leading-6 text-muted-foreground">
                  Entity type coverage will appear after extraction completes.
                </p>
              )}
            </div>
          </Panel>
        </div>
      </section>

      {/* ── Spend Summary ── */}
      <section>
        <SectionLabel>Spend Overview</SectionLabel>
        <div className="rounded-lg border border-border bg-card">
          <div className="border-t-2 border-indigo-500 rounded-t-lg" />
          <div className="p-6">
            <div className="flex items-center gap-2.5 mb-6">
              <div className="flex size-8 items-center justify-center rounded-full bg-indigo-50">
                <DollarSign className="size-4 text-indigo-600" />
              </div>
              <div>
                <h2 className="text-base font-semibold text-foreground">Spend Summary</h2>
                <p className="text-xs text-muted-foreground">Aggregated procurement spend across all vendors</p>
              </div>
            </div>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <div className="rounded-lg border-2 border-indigo-100 bg-indigo-50/40 p-4">
                <p className="text-xs font-medium uppercase tracking-wide text-indigo-600/70">Total</p>
                <p className="mt-2 text-2xl font-bold tabular-nums text-indigo-700">{formatCurrency(data.spend?.total_amount)}</p>
              </div>
              <SpendStatBox label="Average" value={formatCurrency(data.spend?.average_amount)} />
              <SpendStatBox label="Minimum" value={formatCurrency(data.spend?.min_amount)} />
              <SpendStatBox label="Maximum" value={formatCurrency(data.spend?.max_amount)} />
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   Sub-components — visual only, no data fetching
   ═══════════════════════════════════════════════════════════ */

const accentMap = {
  indigo: {
    border: "border-l-indigo-500",
    bg: "bg-indigo-50",
    text: "text-indigo-600",
  },
  emerald: {
    border: "border-l-emerald-500",
    bg: "bg-emerald-50",
    text: "text-emerald-600",
  },
  amber: {
    border: "border-l-amber-500",
    bg: "bg-amber-50",
    text: "text-amber-600",
  },
  violet: {
    border: "border-l-violet-500",
    bg: "bg-violet-50",
    text: "text-violet-600",
  },
} as const;

type AccentColor = keyof typeof accentMap;

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="mb-3 text-[11px] font-semibold uppercase tracking-widest text-muted-foreground/70">
      {children}
    </p>
  );
}

function Metric({
  label,
  value,
  icon: Icon,
  accent,
}: {
  label: string;
  value: string;
  icon: React.ComponentType<{ className?: string }>;
  accent: AccentColor;
}) {
  const tone = accentMap[accent];

  return (
    <div className={cn("rounded-lg border border-border border-l-[3px] bg-card p-5", tone.border)}>
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-medium text-muted-foreground">{label}</p>
        <div className={cn("flex size-9 items-center justify-center rounded-full", tone.bg)}>
          <Icon className={cn("size-4", tone.text)} />
        </div>
      </div>
      <p className="mt-3 text-3xl font-semibold tabular-nums tracking-tight text-foreground">{value}</p>
    </div>
  );
}

function Panel({
  title,
  description,
  icon: Icon,
  accentColor,
  children,
}: {
  title: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  accentColor: AccentColor;
  children: React.ReactNode;
}) {
  const tone = accentMap[accentColor];

  return (
    <div className="rounded-lg border border-border bg-card overflow-hidden">
      <div className={cn("h-0.5", `bg-${accentColor}-400`)} style={{ backgroundColor: `var(--panel-accent-${accentColor})` }} />
      {/* Inline the accent color since dynamic Tailwind classes might not be compiled */}
      <style>{`
        :root {
          --panel-accent-indigo: #818cf8;
          --panel-accent-emerald: #34d399;
          --panel-accent-amber: #fbbf24;
          --panel-accent-violet: #a78bfa;
        }
      `}</style>
      <div className="p-5">
        <div className="flex items-center gap-2.5">
          <div className={cn("flex size-7 items-center justify-center rounded-full", tone.bg)}>
            <Icon className={cn("size-3.5", tone.text)} />
          </div>
          <div>
            <h2 className="text-base font-semibold text-foreground">{title}</h2>
          </div>
        </div>
        <p className="mt-1 ml-[38px] text-sm text-muted-foreground">{description}</p>
        <div className="mt-5">{children}</div>
      </div>
    </div>
  );
}

function DetailCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-muted/20 p-3.5">
      <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="mt-1.5 text-sm font-semibold text-foreground">{value}</p>
    </div>
  );
}

const riskBarColors: Record<string, string> = {
  low: "bg-emerald-500",
  medium: "bg-amber-500",
  high: "bg-orange-500",
  critical: "bg-red-500",
};

function BarRow({ label, value, max }: { label: string; value: number; max: number }) {
  const pct = max > 0 ? Math.max(4, Math.round((value / max) * 100)) : 0;
  const normalizedLabel = label.toLowerCase();
  const barColor = riskBarColors[normalizedLabel] ?? "bg-primary";

  return (
    <div>
      <div className="mb-2 flex items-center justify-between gap-4">
        <StatusBadge value={label} />
        <div className="flex items-center gap-3">
          <span className="text-xs text-muted-foreground tabular-nums">{pct}%</span>
          <span className="text-sm font-semibold tabular-nums w-10 text-right">{formatNumber(value)}</span>
        </div>
      </div>
      <div className="h-2.5 rounded-full bg-muted">
        <div className={cn("h-2.5 rounded-full transition-all", barColor)} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function StatusDot({ status }: { status: string }) {
  const normalized = status.toLowerCase();
  const dotColors: Record<string, string> = {
    completed: "bg-emerald-500",
    processing: "bg-indigo-500",
    pending: "bg-slate-400",
    failed: "bg-red-500",
    indexed: "bg-emerald-500",
  };
  return (
    <span className={cn("inline-block size-2 rounded-full", dotColors[normalized] ?? "bg-slate-400")} />
  );
}

function RankBadge({ rank }: { rank: number }) {
  if (rank <= 3) {
    const tones: Record<number, string> = {
      1: "bg-amber-100 text-amber-700 border-amber-200",
      2: "bg-slate-100 text-slate-600 border-slate-200",
      3: "bg-orange-50 text-orange-600 border-orange-200",
    };
    return (
      <span className={cn("inline-flex size-7 items-center justify-center rounded-full border text-xs font-bold", tones[rank])}>
        {rank}
      </span>
    );
  }
  return <span className="inline-flex size-7 items-center justify-center text-sm text-muted-foreground">{rank}</span>;
}

const entityTagColors = [
  "bg-indigo-50 text-indigo-700 border-indigo-200",
  "bg-emerald-50 text-emerald-700 border-emerald-200",
  "bg-amber-50 text-amber-700 border-amber-200",
  "bg-violet-50 text-violet-700 border-violet-200",
  "bg-rose-50 text-rose-700 border-rose-200",
  "bg-cyan-50 text-cyan-700 border-cyan-200",
  "bg-orange-50 text-orange-700 border-orange-200",
  "bg-teal-50 text-teal-700 border-teal-200",
];

const entityBarColors = [
  "bg-indigo-400",
  "bg-emerald-400",
  "bg-amber-400",
  "bg-violet-400",
  "bg-rose-400",
  "bg-cyan-400",
  "bg-orange-400",
  "bg-teal-400",
];

function EntityTypeRow({ entityType, count, maxCount }: { entityType: string; count: number; maxCount: number }) {
  // Deterministic color index from entity type string
  const hash = entityType.split("").reduce((acc, c) => acc + c.charCodeAt(0), 0);
  const colorIdx = hash % entityTagColors.length;
  const barWidth = Math.max(8, Math.round((count / maxCount) * 100));

  return (
    <div className="flex items-center gap-3">
      <span className={cn("inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium shrink-0", entityTagColors[colorIdx])}>
        {titleCase(entityType)}
      </span>
      <div className="flex-1 h-1.5 rounded-full bg-muted">
        <div className={cn("h-1.5 rounded-full", entityBarColors[colorIdx])} style={{ width: `${barWidth}%` }} />
      </div>
      <span className="text-sm font-semibold tabular-nums text-foreground w-12 text-right shrink-0">{formatNumber(count)}</span>
    </div>
  );
}

function SpendStatBox({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-muted/20 p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="mt-2 text-lg font-semibold tabular-nums text-foreground">{value}</p>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   Utility helpers — unchanged logic
   ═══════════════════════════════════════════════════════════ */

function formatMetricPercent(value: number | null | undefined): string {
  return `${(value ?? 0).toFixed(1)}%`;
}

function getSettledError(results: PromiseSettledResult<unknown>[]): string | null {
  const messages = results
    .filter((result) => result.status === "rejected")
    .map((result) => result.reason)
    .map((reason) => (reason instanceof Error ? reason.message : "Analytics could not be loaded."));

  return messages.length > 0 ? [...new Set(messages)].join(" ") : null;
}

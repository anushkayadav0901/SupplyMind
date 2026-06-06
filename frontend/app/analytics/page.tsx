import type React from "react";
import { AlertCircle, BarChart3, FileText, PieChart, TrendingUp } from "lucide-react";
import { EmptyState } from "@/components/empty-state";
import { StatusBadge } from "@/components/status-badge";
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
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Analytics</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Processing health, extraction quality, spend signals, vendor concentration, and risk distribution.
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

      <section className="grid gap-4 md:grid-cols-4">
        <Metric label="OCR Success" value={formatMetricPercent(data.documents?.ocr_success_rate)} icon={FileText} />
        <Metric label="Average Risk" value={formatMetricPercent((data.risk?.average_risk_score ?? 0) * 100)} icon={PieChart} />
        <Metric label="Total Spend" value={formatCurrency(data.spend?.total_amount)} icon={TrendingUp} />
        <Metric label="Extraction Rate" value={formatMetricPercent(data.extraction?.extraction_rate_percent)} icon={BarChart3} />
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <Panel title="Risk Distribution" description="Latest prediction labels across vendors.">
          <div className="space-y-4">
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

        <Panel title="Document Processing" description="Status and OCR method coverage.">
          <div className="grid gap-4 sm:grid-cols-2">
            <Detail label="Total Documents" value={formatNumber(data.documents?.total_documents)} />
            <Detail label="Pages Processed" value={formatNumber(data.documents?.total_pages_processed)} />
            <Detail label="Average File Size" value={formatBytes(data.documents?.average_file_size_bytes)} />
            <Detail label="Latest Upload" value={formatDate(data.documents?.latest_upload_at)} />
          </div>
          {Object.entries(data.documents?.status_breakdown ?? {}).length > 0 ? (
            <div className="mt-5 space-y-3">
              {Object.entries(data.documents?.status_breakdown ?? {}).map(([status, count]) => (
                <div key={status} className="flex items-center justify-between gap-4">
                  <StatusBadge value={status} />
                  <span className="text-sm font-medium">{formatNumber(count)}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="mt-5 text-sm leading-6 text-muted-foreground">
              Processing status breakdown will appear once documents are uploaded.
            </p>
          )}
        </Panel>
      </section>

      <section className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
        <Panel title="Top Vendors" description="Vendors ranked by extracted procurement value.">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead className="border-b border-border text-xs uppercase text-muted-foreground">
                <tr>
                  <th className="py-2 pr-3 font-medium">Rank</th>
                  <th className="py-2 pr-3 font-medium">Vendor</th>
                  <th className="py-2 pr-3 font-medium">Spend</th>
                  <th className="py-2 pr-3 font-medium">Risk</th>
                  <th className="py-2 pr-3 font-medium">Docs</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {(data.topVendors?.top_vendors ?? []).length > 0 ? (
                  data.topVendors?.top_vendors.map((vendor) => (
                    <tr key={`${vendor.rank}-${vendor.vendor_id}`}>
                      <td className="py-3 pr-3 text-muted-foreground">{vendor.rank}</td>
                      <td className="py-3 pr-3 font-medium">{vendor.vendor_name}</td>
                      <td className="py-3 pr-3">{formatCurrency(vendor.total_value)}</td>
                      <td className="py-3 pr-3">
                        <StatusBadge value={vendor.latest_risk_label ?? "unscored"} />
                      </td>
                      <td className="py-3 pr-3 text-muted-foreground">{formatNumber(vendor.document_count)}</td>
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

        <Panel title="Extraction Summary" description="Entity quality and field coverage.">
          <div className="space-y-4">
            <Detail label="Entities" value={formatNumber(data.extraction?.total_entities)} />
            <Detail label="Documents With Extractions" value={formatNumber(data.extraction?.documents_with_extractions)} />
            <Detail label="Vendor Link Rate" value={formatMetricPercent(data.extraction?.vendor_link_rate_percent)} />
            <Detail
              label="Average Confidence"
              value={data.extraction?.average_confidence_score != null ? formatMetricPercent(data.extraction.average_confidence_score * 100) : "Not available"}
            />
          </div>
          <div className="mt-5 space-y-3">
            {Object.entries(data.extraction?.entity_type_breakdown ?? {}).length > 0 ? (
              Object.entries(data.extraction?.entity_type_breakdown ?? {}).map(([entityType, count]) => (
                <div key={entityType} className="flex items-center justify-between gap-4">
                  <span className="text-sm text-muted-foreground">{titleCase(entityType)}</span>
                  <span className="text-sm font-medium">{formatNumber(count)}</span>
                </div>
              ))
            ) : (
              <p className="text-sm leading-6 text-muted-foreground">
                Entity type coverage will appear after extraction completes.
              </p>
            )}
          </div>
        </Panel>
      </section>

      <section className="rounded-lg border border-border bg-card p-5">
        <h2 className="text-base font-semibold">Spend Summary</h2>
        <div className="mt-5 grid gap-4 md:grid-cols-4">
          <Detail label="Total" value={formatCurrency(data.spend?.total_amount)} />
          <Detail label="Average" value={formatCurrency(data.spend?.average_amount)} />
          <Detail label="Minimum" value={formatCurrency(data.spend?.min_amount)} />
          <Detail label="Maximum" value={formatCurrency(data.spend?.max_amount)} />
        </div>
      </section>
    </div>
  );
}

function Metric({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: string;
  icon: React.ComponentType<{ className?: string }>;
}) {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm text-muted-foreground">{label}</p>
        <Icon className="size-4 text-muted-foreground" />
      </div>
      <p className="mt-3 text-2xl font-semibold">{value}</p>
    </div>
  );
}

function Panel({ title, description, children }: { title: string; description: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-border bg-card p-5">
      <h2 className="text-base font-semibold">{title}</h2>
      <p className="mt-1 text-sm text-muted-foreground">{description}</p>
      <div className="mt-5">{children}</div>
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-2 text-sm font-medium">{value}</p>
    </div>
  );
}

function BarRow({ label, value, max }: { label: string; value: number; max: number }) {
  const width = max > 0 ? Math.max(4, Math.round((value / max) * 100)) : 0;

  return (
    <div>
      <div className="mb-2 flex items-center justify-between gap-4">
        <StatusBadge value={label} />
        <span className="text-sm font-medium">{formatNumber(value)}</span>
      </div>
      <div className="h-2 rounded-full bg-muted">
        <div className="h-2 rounded-full bg-primary" style={{ width: `${width}%` }} />
      </div>
    </div>
  );
}

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

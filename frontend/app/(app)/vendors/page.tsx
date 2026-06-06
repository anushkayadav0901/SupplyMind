import type React from "react";
import { AlertCircle, FileText, Mail, Phone, ShieldAlert, Users } from "lucide-react";
import { EmptyState } from "@/components/empty-state";
import { StatusBadge } from "@/components/status-badge";
import { api } from "@/lib/api";
import { formatDate, formatNumber, formatPercent } from "@/lib/format";
import type { RiskSummary, VendorListItem } from "@/lib/types";

async function getVendorsData(): Promise<{
  vendors: VendorListItem[];
  riskSummary: RiskSummary | null;
  error: string | null;
}> {
  const [vendorsResult, riskSummaryResult] = await Promise.allSettled([
    api.listVendors(0, 100),
    api.getRiskSummary(),
  ]);

  const vendors = vendorsResult.status === "fulfilled" ? vendorsResult.value : [];
  const riskSummary = riskSummaryResult.status === "fulfilled" ? riskSummaryResult.value : null;
  const errors = [vendorsResult, riskSummaryResult]
    .filter((result) => result.status === "rejected")
    .map((result) => result.reason)
    .map((reason) => (reason instanceof Error ? reason.message : "Vendor data could not be loaded."));

  return {
    vendors,
    riskSummary,
    error: [...new Set(errors)].join(" "),
  };
}

const summaryAccents: Record<string, string> = {
  "Total Vendors": "border-l-indigo-500",
  "Risk Scored": "border-l-emerald-500",
  "Elevated Risk": "border-l-red-500",
  "With Email": "border-l-amber-500",
};

const riskLabelAccents: Record<string, string> = {
  low: "border-l-emerald-500",
  medium: "border-l-amber-500",
  high: "border-l-orange-500",
  critical: "border-l-red-500",
};

export default async function VendorsPage() {
  const { vendors, riskSummary, error } = await getVendorsData();
  const scored = vendors.filter((vendor) => vendor.latest_risk_score != null).length;
  const withEmail = vendors.filter((vendor) => vendor.contact_email).length;
  const elevated = vendors.filter((vendor) =>
    ["high", "critical"].includes(vendor.latest_risk_label?.toLowerCase() ?? "")
  ).length;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Vendors</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Vendor intelligence, linked documents, contact coverage, and latest ML risk labels.
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

      <section>
        <p className="mb-3 text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
          Overview
        </p>
        <div className="grid gap-4 md:grid-cols-4">
          <SummaryCard label="Total Vendors" value={formatNumber(vendors.length)} icon={Users} />
          <SummaryCard label="Risk Scored" value={formatNumber(scored)} icon={ShieldAlert} />
          <SummaryCard label="Elevated Risk" value={formatNumber(elevated)} icon={ShieldAlert} />
          <SummaryCard label="With Email" value={formatNumber(withEmail)} icon={Mail} />
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-[0.8fr_1.2fr]">
        <div className="rounded-lg border border-border bg-card p-5">
          <p className="mb-3 text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
            Distribution
          </p>
          <h2 className="text-base font-semibold">Risk Labels</h2>
          <div className="mt-4 space-y-2.5">
            {["low", "medium", "high", "critical"].map((label) => (
              <div
                key={label}
                className={`flex items-center justify-between gap-4 rounded-md border border-border border-l-[3px] ${riskLabelAccents[label]} bg-muted/20 px-3 py-2.5`}
              >
                <StatusBadge value={label} />
                <span className="text-sm font-semibold tabular-nums">
                  {formatNumber(riskSummary?.distribution[label] ?? 0)}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-lg border border-border bg-card">
          <div className="border-b border-border p-5">
            <p className="mb-2 text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
              Registry
            </p>
            <h2 className="text-base font-semibold">Vendor Register</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              {vendors.length > 0
                ? "Latest vendor rows with document counts and risk model output."
                : "Vendors appear here after document extraction links suppliers to procurement files."}
            </p>
          </div>
          {vendors.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[820px] text-left text-sm">
                <thead className="border-b border-border bg-muted/50 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  <tr>
                    <th className="px-4 py-3 font-semibold">Vendor</th>
                    <th className="px-4 py-3 font-semibold">Contact</th>
                    <th className="px-4 py-3 font-semibold">Risk</th>
                    <th className="px-4 py-3 font-semibold">Score</th>
                    <th className="px-4 py-3 font-semibold">Documents</th>
                    <th className="px-4 py-3 font-semibold">Added</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {vendors.map((vendor, index) => (
                      <tr
                        key={vendor.id}
                        className={`transition-colors hover:bg-muted/40 ${index % 2 === 1 ? "bg-muted/20" : ""}`}
                      >
                        <td className="px-4 py-3">
                          <p className="font-semibold text-foreground">{vendor.name}</p>
                          {vendor.gstin ? (
                            <span className="mt-1 inline-block rounded border border-border bg-muted/40 px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">
                              {vendor.gstin}
                            </span>
                          ) : (
                            <p className="mt-1 text-xs text-muted-foreground">GSTIN not captured</p>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <div className="space-y-1 text-xs text-muted-foreground">
                            <span className="flex items-center gap-1.5">
                              <Mail className="size-3" />
                              {vendor.contact_email ?? "No email"}
                            </span>
                            <span className="flex items-center gap-1.5">
                              <Phone className="size-3" />
                              {vendor.contact_phone ?? "No phone"}
                            </span>
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <StatusBadge value={vendor.latest_risk_label ?? "unscored"} />
                        </td>
                        <td className="px-4 py-3 font-medium tabular-nums">
                          {vendor.latest_risk_score != null ? formatPercent(vendor.latest_risk_score) : "Not scored"}
                        </td>
                        <td className="px-4 py-3 text-muted-foreground">
                          {formatNumber(vendor.document_count)}
                        </td>
                        <td className="px-4 py-3 text-muted-foreground">{formatDate(vendor.created_at)}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-5">
              <EmptyState
                icon={FileText}
                title={error ? "Vendor data is temporarily unavailable" : "No vendors detected yet"}
                framed={false}
                description={
                  error
                    ? "The page is ready, but the backend could not be reached. Start the FastAPI server and refresh to load vendor intelligence."
                    : "Upload invoices, purchase orders, or contracts. SupplyMind will extract supplier entities, link documents, and show risk labels here."
                }
                action={error ? undefined : { label: "Go to documents", href: "/documents" }}
              />
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

function SummaryCard({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: string;
  icon: React.ComponentType<{ className?: string }>;
}) {
  const accent = summaryAccents[label] ?? "border-l-border";
  return (
    <div className={`rounded-lg border border-border border-l-[3px] ${accent} bg-card p-4`}>
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
        <div className="flex size-8 items-center justify-center rounded-full bg-muted/60">
          <Icon className="size-4 text-muted-foreground" />
        </div>
      </div>
      <p className="mt-3 text-3xl font-semibold tabular-nums">{value}</p>
    </div>
  );
}

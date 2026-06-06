import { cn } from "@/lib/utils";
import { titleCase } from "@/lib/format";

const toneByValue: Record<string, string> = {
  completed: "border-emerald-200 bg-emerald-50 text-emerald-700",
  processing: "border-indigo-200 bg-indigo-50 text-indigo-700",
  pending: "border-slate-200 bg-slate-50 text-slate-700",
  failed: "border-red-200 bg-red-50 text-red-700",
  low: "border-emerald-200 bg-emerald-50 text-emerald-700",
  medium: "border-amber-200 bg-amber-50 text-amber-700",
  high: "border-orange-200 bg-orange-50 text-orange-700",
  critical: "border-red-200 bg-red-50 text-red-700",
  unscored: "border-slate-200 bg-slate-50 text-slate-700",
  indexed: "border-emerald-200 bg-emerald-50 text-emerald-700",
  offline: "border-slate-200 bg-slate-50 text-slate-700",
};

interface StatusBadgeProps {
  value: string | null | undefined;
  className?: string;
}

export function StatusBadge({ value, className }: StatusBadgeProps) {
  const normalized = value?.toLowerCase() ?? "unknown";

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium",
        toneByValue[normalized] ?? "border-slate-200 bg-slate-50 text-slate-700",
        className
      )}
    >
      {titleCase(value)}
    </span>
  );
}

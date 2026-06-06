import { cn } from "@/lib/utils";
import { titleCase } from "@/lib/format";

const toneByValue: Record<string, { badge: string; dot: string }> = {
  completed: {
    badge: "border-emerald-200 bg-emerald-50 text-emerald-700",
    dot: "bg-emerald-500",
  },
  processing: {
    badge: "border-indigo-200 bg-indigo-50 text-indigo-700",
    dot: "bg-indigo-500",
  },
  pending: {
    badge: "border-slate-200 bg-slate-50 text-slate-600",
    dot: "bg-slate-400",
  },
  failed: {
    badge: "border-red-200 bg-red-50 text-red-700",
    dot: "bg-red-500",
  },
  low: {
    badge: "border-emerald-200 bg-emerald-50 text-emerald-700",
    dot: "bg-emerald-500",
  },
  medium: {
    badge: "border-amber-200 bg-amber-50 text-amber-700",
    dot: "bg-amber-500",
  },
  high: {
    badge: "border-orange-200 bg-orange-50 text-orange-700",
    dot: "bg-orange-500",
  },
  critical: {
    badge: "border-red-200 bg-red-50 text-red-700",
    dot: "bg-red-500",
  },
  unscored: {
    badge: "border-slate-200 bg-slate-50 text-slate-600",
    dot: "bg-slate-400",
  },
  indexed: {
    badge: "border-emerald-200 bg-emerald-50 text-emerald-700",
    dot: "bg-emerald-500",
  },
  offline: {
    badge: "border-slate-200 bg-slate-50 text-slate-600",
    dot: "bg-slate-400",
  },
  unknown: {
    badge: "border-slate-200 bg-slate-50 text-slate-500",
    dot: "bg-slate-300",
  },
};

const fallbackTone = {
  badge: "border-slate-200 bg-slate-50 text-slate-500",
  dot: "bg-slate-300",
};

interface StatusBadgeProps {
  value: string | null | undefined;
  className?: string;
}

export function StatusBadge({ value, className }: StatusBadgeProps) {
  const normalized = value?.toLowerCase() ?? "unknown";
  const tone = toneByValue[normalized] ?? fallbackTone;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md border px-2.5 py-0.5 text-xs font-medium tracking-wide",
        tone.badge,
        className
      )}
    >
      <span
        className={cn("size-1.5 shrink-0 rounded-full", tone.dot)}
        aria-hidden="true"
      />
      {titleCase(value)}
    </span>
  );
}

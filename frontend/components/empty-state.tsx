import Link from "next/link";
import type React from "react";

interface EmptyStateProps {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  description: string;
  framed?: boolean;
  action?: {
    label: string;
    href: string;
  };
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  framed = true,
  action,
}: EmptyStateProps) {
  return (
    <div
      className={
        framed
          ? "flex min-h-64 flex-col items-center justify-center rounded-lg border border-dashed border-border bg-muted/10 px-8 py-12 text-center"
          : "flex min-h-64 flex-col items-center justify-center px-8 py-12 text-center"
      }
    >
      <div className="flex size-12 items-center justify-center rounded-lg border border-border bg-muted/40 text-muted-foreground">
        <Icon className="size-5.5" />
      </div>
      <h3 className="mt-5 text-[15px] font-semibold tracking-tight text-foreground">
        {title}
      </h3>
      <p className="mt-1.5 max-w-sm text-sm leading-relaxed text-muted-foreground">
        {description}
      </p>
      {action ? (
        <Link
          href={action.href}
          className="mt-6 inline-flex h-9 items-center justify-center rounded-md bg-primary px-4 text-sm font-medium tracking-tight text-primary-foreground transition-colors hover:bg-primary/90"
        >
          {action.label}
        </Link>
      ) : null}
    </div>
  );
}

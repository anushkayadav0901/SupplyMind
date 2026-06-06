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
          ? "flex min-h-56 flex-col items-center justify-center rounded-lg border border-dashed border-border bg-muted/20 px-6 py-10 text-center"
          : "flex min-h-56 flex-col items-center justify-center px-6 py-10 text-center"
      }
    >
      <div className="flex size-10 items-center justify-center rounded-md border border-border bg-background text-muted-foreground">
        <Icon className="size-5" />
      </div>
      <h3 className="mt-4 text-base font-semibold text-foreground">{title}</h3>
      <p className="mt-2 max-w-md text-sm leading-6 text-muted-foreground">
        {description}
      </p>
      {action ? (
        <Link
          href={action.href}
          className="mt-5 inline-flex h-8 items-center justify-center rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/85"
        >
          {action.label}
        </Link>
      ) : null}
    </div>
  );
}

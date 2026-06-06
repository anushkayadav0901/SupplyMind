"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  FileText,
  Users,
  BarChart3,
  MessageSquareText,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Documents", href: "/documents", icon: FileText },
  { label: "Vendors", href: "/vendors", icon: Users },
  { label: "Analytics", href: "/analytics", icon: BarChart3 },
  { label: "RAG Assistant", href: "/rag", icon: MessageSquareText },
] as const;

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-full w-56 flex-col border-r border-border bg-sidebar">
      {/* Logo / brand */}
      <div className="flex h-16 items-center gap-2.5 border-b border-border/60 px-5">
        <Link href="/dashboard" className="flex items-center gap-2.5">
          <span className="flex size-7 items-center justify-center rounded-md bg-primary text-xs font-bold text-primary-foreground">
            S
          </span>
          <span className="text-[15px] font-semibold tracking-tight text-foreground">
            SupplyMind
          </span>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 pt-5">
        <p className="mb-2 px-2.5 text-[10.5px] font-semibold uppercase tracking-widest text-muted-foreground/60">
          Navigation
        </p>
        <div className="space-y-0.5">
          {NAV_ITEMS.map(({ label, href, icon: Icon }) => {
            const isActive =
              pathname === href || pathname.startsWith(`${href}/`);

            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "flex items-center gap-2.5 rounded-md px-2.5 py-2.5 text-[13.5px] font-medium transition-colors",
                  isActive
                    ? "bg-sidebar-accent text-sidebar-primary"
                    : "text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-foreground"
                )}
              >
                <Icon className="size-4 shrink-0" />
                {label}
              </Link>
            );
          })}
        </div>
      </nav>

      {/* Footer */}
      <div className="border-t border-border px-5 py-3.5">
        <p className="text-[10.5px] font-medium tracking-wide text-muted-foreground/50">
          SupplyMind v0.1.0
        </p>
      </div>
    </aside>
  );
}

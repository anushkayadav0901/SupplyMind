import { Sidebar } from "./sidebar";

interface ShellProps {
  children: React.ReactNode;
}

export function Shell({ children }: ShellProps) {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top header bar */}
        <header className="flex h-14 shrink-0 items-center border-b border-border/70 bg-background px-6 shadow-[0_1px_2px_0_rgba(0,0,0,0.03)]">
          <div className="flex-1" />
          <div className="flex items-center gap-3">
            <div className="flex size-8 items-center justify-center rounded-full bg-slate-100 text-xs font-semibold tracking-tight text-slate-600 ring-1 ring-slate-200/80">
              AY
            </div>
          </div>
        </header>

        {/* Main content area */}
        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-6xl px-6 py-8">{children}</div>
        </main>
      </div>
    </div>
  );
}

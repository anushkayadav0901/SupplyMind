"use client";

import Link from "next/link";
import {
  ArrowRight,
  ExternalLink,
  Sun,
  FileText,
  Users,
  ShieldCheck,
  TrendingUp,
  LayoutDashboard,
  BarChart3,
  MessageSquareText,
  Settings,
  ArrowUp,
  ArrowDown,
  Sparkles,
  Search,
  CloudLightning,
  Upload,
  Cpu,
  Brain,
  Database,
  ArrowRightLeft,
} from "lucide-react";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-white flex flex-col font-sans antialiased text-slate-800">
      
      {/* ── HEADER NAVIGATION ── */}
      <header className="sticky top-0 z-50 w-full border-b border-slate-100 bg-white/95 backdrop-blur-sm px-6 py-3.5">
        <div className="mx-auto max-w-7xl flex items-center justify-between">
          
          {/* Logo */}
          <div className="flex items-center gap-2.5">
            <div className="flex size-9 items-center justify-center rounded-xl bg-[#f97316] text-white font-bold text-xl shadow-sm">
              S
            </div>
            <span className="text-xl font-bold tracking-tight text-slate-900">SupplyMind</span>
          </div>

          {/* Links */}
          <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-slate-600">
            <Link href="#product" className="hover:text-slate-900 transition-colors">Product</Link>
            <Link href="#features" className="hover:text-slate-900 transition-colors">Features</Link>
            <Link href="#how-it-works" className="hover:text-slate-900 transition-colors">How It Works</Link>
            <Link href="#pricing" className="hover:text-slate-900 transition-colors">Pricing</Link>
            <a href="http://127.0.0.1:8000/api/v1/docs" target="_blank" rel="noopener noreferrer" className="hover:text-slate-900 transition-colors">Docs</a>
            <Link href="#contact" className="hover:text-slate-900 transition-colors">Contact</Link>
          </nav>

          {/* Right side items */}
          <div className="flex items-center gap-4">
            <button className="p-2 text-slate-400 hover:text-slate-600 transition-colors rounded-lg hover:bg-slate-50">
              <Sun className="size-5" />
            </button>
            <Link href="/dashboard" className="text-sm font-semibold text-slate-700 hover:text-slate-900 transition-colors">
              Sign in
            </Link>
            <Link
              href="/dashboard"
              className="inline-flex h-10 items-center justify-center rounded-xl bg-[#f97316] px-5 text-sm font-semibold text-white hover:bg-[#ea580c] transition-colors gap-1.5 shadow-sm"
            >
              Launch Console <ArrowRight className="size-4" />
            </Link>
          </div>
        </div>
      </header>

      {/* ── HERO SPLIT SECTION ── */}
      <section id="product" className="mx-auto max-w-7xl px-6 pt-12 pb-20 grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
        
        {/* Left Content */}
        <div className="lg:col-span-5 flex flex-col items-start text-left">
          
          {/* Pill Badge */}
          <div className="inline-flex items-center gap-1.5 rounded-full border border-orange-100 bg-orange-50/70 px-3 py-1 text-xs font-semibold text-[#f97316] mb-6 tracking-wide uppercase">
            <Sparkles className="size-3.5 fill-orange-100" /> AI-powered procurement intelligence
          </div>

          {/* Headline */}
          <h1 className="text-[40px] sm:text-[46px] font-black tracking-tight text-slate-900 leading-[1.1] mb-6">
            Transform Raw Procurement Documents into <span className="text-[#f97316]">Risk Intelligence</span>
          </h1>

          {/* Subheading */}
          <p className="text-base text-slate-500 leading-relaxed mb-8 max-w-lg">
            Automate document ingestion, extract structured contract data with high-accuracy LLMs, predict vendor late-delivery risks, and search your entire supply corpus using RAG.
          </p>

          {/* Call to Actions */}
          <div className="flex flex-col sm:flex-row items-center gap-3.5 w-full sm:w-auto mb-8">
            <Link
              href="/dashboard"
              className="w-full sm:w-auto inline-flex h-12 items-center justify-center rounded-xl bg-[#f97316] px-6 text-base font-semibold text-white hover:bg-[#ea580c] transition-colors gap-1.5 shadow-sm"
            >
              Launch Console <ArrowRight className="size-5" />
            </Link>
            <a
              href="http://127.0.0.1:8000/api/v1/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="w-full sm:w-auto inline-flex h-12 items-center justify-center rounded-xl border border-slate-200 bg-white px-6 text-base font-semibold text-slate-600 hover:bg-slate-50 transition-colors gap-1.5"
            >
              Explore REST APIs <ExternalLink className="size-4 text-slate-400" />
            </a>
          </div>

          {/* Key Checklist Info */}
          <div className="flex flex-wrap items-center gap-x-6 gap-y-3 mb-12 text-xs font-medium text-slate-500">
            <div className="flex items-center gap-1.5">
              <span className="size-1.5 rounded-full bg-[#f97316]" /> No credit card required
            </div>
            <div className="flex items-center gap-1.5">
              <span className="size-1.5 rounded-full bg-[#f97316]" /> Setup in minutes
            </div>
            <div className="flex items-center gap-1.5">
              <span className="size-1.5 rounded-full bg-[#f97316]" /> Enterprise ready
            </div>
          </div>

          {/* Trusted Companies */}
          <div className="w-full border-t border-slate-100 pt-8">
            <p className="text-[11px] font-bold tracking-widest text-slate-400 uppercase mb-4">
              Trusted by procurement teams worldwide
            </p>
            <div className="grid grid-cols-3 sm:grid-cols-6 gap-5 items-center opacity-60">
              <span className="text-xs font-black tracking-wider text-slate-800">Globex</span>
              <span className="text-xs font-bold tracking-tight text-slate-800">ACME CORP</span>
              <span className="text-xs font-mono font-bold text-slate-800">INITECH</span>
              <span className="text-xs font-serif font-black italic text-slate-800">Stark</span>
              <span className="text-xs font-semibold tracking-tighter text-slate-800">Wayne Ent.</span>
              <span className="text-xs font-bold tracking-widest text-slate-800 text-opacity-80">OSCORP</span>
            </div>
          </div>
        </div>

        {/* Right Preview - Live-built Dashboard Preview */}
        <div className="lg:col-span-7 border border-slate-200/90 rounded-2xl bg-white p-2.5 shadow-[0_24px_48px_-15px_rgba(0,0,0,0.06)] select-none">
          <div className="border border-slate-100/80 rounded-xl bg-slate-50/50 flex h-[480px] overflow-hidden text-slate-800 font-sans text-xs">
            
            {/* Mock Sidebar */}
            <aside className="w-40 border-r border-slate-200/80 bg-white flex flex-col p-3.5 shrink-0 justify-between">
              <div className="space-y-6">
                <div className="flex items-center gap-1.5">
                  <div className="flex size-6 items-center justify-center rounded bg-[#f97316] text-white font-bold text-sm">S</div>
                  <span className="font-bold text-slate-900 tracking-tight text-[11px]">SupplyMind</span>
                </div>
                <div className="space-y-1">
                  <div className="flex items-center gap-2 px-2 py-1.5 rounded bg-orange-50 text-[#f97316] font-semibold">
                    <LayoutDashboard className="size-3.5" /> Dashboard
                  </div>
                  <div className="flex items-center gap-2 px-2 py-1.5 text-slate-500 hover:text-slate-800">
                    <FileText className="size-3.5" /> Documents
                  </div>
                  <div className="flex items-center gap-2 px-2 py-1.5 text-slate-500 hover:text-slate-800">
                    <Users className="size-3.5" /> Vendors
                  </div>
                  <div className="flex items-center gap-2 px-2 py-1.5 text-slate-500 hover:text-slate-800">
                    <BarChart3 className="size-3.5" /> Analytics
                  </div>
                  <div className="flex items-center gap-2 px-2 py-1.5 text-slate-500 hover:text-slate-800">
                    <MessageSquareText className="size-3.5" /> RAG Assistant
                  </div>
                  <div className="flex items-center gap-2 px-2 py-1.5 text-slate-500 hover:text-slate-800">
                    <Settings className="size-3.5" /> Settings
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2 border-t border-slate-100 pt-3">
                <div className="size-6 rounded bg-slate-200 text-slate-600 font-bold flex items-center justify-center text-[10px]">N</div>
                <span className="text-[10px] text-slate-400 font-medium">SupplyMind v0.1.0</span>
              </div>
            </aside>

            {/* Mock Main Dashboard View */}
            <main className="flex-1 overflow-y-auto p-4 space-y-4">
              
              {/* Header */}
              <div>
                <h2 className="text-sm font-bold text-slate-900">Dashboard</h2>
                <p className="text-[10px] text-slate-400">Procurement overview, document processing, vendor coverage, and risk signals.</p>
              </div>

              {/* 4 Cards */}
              <div className="grid grid-cols-4 gap-2">
                <div className="bg-white border border-slate-200/80 p-2.5 rounded-lg">
                  <div className="text-[9px] font-semibold text-slate-400">Documents Processed</div>
                  <div className="text-sm font-black text-slate-900 mt-1">5,248</div>
                  <div className="text-[8px] text-emerald-600 flex items-center gap-0.5 mt-0.5"><ArrowUp className="size-2" /> 12.5% this month</div>
                </div>
                <div className="bg-white border border-slate-200/80 p-2.5 rounded-lg">
                  <div className="text-[9px] font-semibold text-slate-400">Vendors Identified</div>
                  <div className="text-sm font-black text-slate-900 mt-1">1,243</div>
                  <div className="text-[8px] text-emerald-600 flex items-center gap-0.5 mt-0.5"><ArrowUp className="size-2" /> 8.1% this month</div>
                </div>
                <div className="bg-white border border-slate-200/80 p-2.5 rounded-lg">
                  <div className="text-[9px] font-semibold text-slate-400">Total Spend</div>
                  <div className="text-sm font-black text-slate-900 mt-1">$1.39M</div>
                  <div className="text-[8px] text-emerald-600 flex items-center gap-0.5 mt-0.5"><ArrowUp className="size-2" /> 15.3% this month</div>
                </div>
                <div className="bg-white border border-slate-200/80 p-2.5 rounded-lg">
                  <div className="text-[9px] font-semibold text-slate-400">Elevated Risk Vendors</div>
                  <div className="text-sm font-black text-slate-900 mt-1">23</div>
                  <div className="text-[8px] text-rose-600 flex items-center gap-0.5 mt-0.5"><ArrowDown className="size-2" /> 4.2% this month</div>
                </div>
              </div>

              {/* 2 Charts row */}
              <div className="grid grid-cols-12 gap-3">
                {/* Spend Over Time line chart */}
                <div className="col-span-7 bg-white border border-slate-200/80 p-3 rounded-lg flex flex-col justify-between">
                  <div className="text-[9px] font-bold text-slate-900">Spend Over Time</div>
                  <div className="h-24 w-full mt-2 relative">
                    <svg className="w-full h-full" viewBox="0 0 100 40">
                      {/* Grid Lines */}
                      <line x1="0" y1="10" x2="100" y2="10" stroke="#f1f5f9" strokeWidth="0.5" />
                      <line x1="0" y1="20" x2="100" y2="20" stroke="#f1f5f9" strokeWidth="0.5" />
                      <line x1="0" y1="30" x2="100" y2="30" stroke="#f1f5f9" strokeWidth="0.5" />
                      <line x1="0" y1="40" x2="100" y2="40" stroke="#e2e8f0" strokeWidth="0.7" />
                      {/* Chart Path */}
                      <path
                        d="M 5 35 L 20 31 L 38 22 L 56 26 L 74 15 L 95 8"
                        fill="none"
                        stroke="#f97316"
                        strokeWidth="1.2"
                      />
                      {/* Points */}
                      <circle cx="5" cy="35" r="1.2" fill="#f97316" />
                      <circle cx="20" cy="31" r="1.2" fill="#f97316" />
                      <circle cx="38" cy="22" r="1.2" fill="#f97316" />
                      <circle cx="56" cy="26" r="1.2" fill="#f97316" />
                      <circle cx="74" cy="15" r="1.2" fill="#f97316" />
                      <circle cx="95" cy="8" r="1.5" fill="#ea580c" />
                    </svg>
                    {/* Axis Labels */}
                    <div className="flex justify-between text-[7px] text-slate-400 mt-1 font-mono">
                      <span>$0</span>
                      <span>Jan</span>
                      <span>Feb</span>
                      <span>Mar</span>
                      <span>Apr</span>
                      <span>May</span>
                      <span>Jun</span>
                    </div>
                  </div>
                </div>

                {/* Risk Distribution donut */}
                <div className="col-span-5 bg-white border border-slate-200/80 p-3 rounded-lg flex flex-col justify-between">
                  <div className="text-[9px] font-bold text-slate-900">Risk Distribution</div>
                  <div className="flex items-center gap-2 mt-2">
                    <div className="relative size-16 flex items-center justify-center shrink-0">
                      {/* Circular ring chart */}
                      <svg className="size-full transform -rotate-90" viewBox="0 0 36 36">
                        <circle cx="18" cy="18" r="15.91" fill="none" stroke="#f1f5f9" strokeWidth="3" />
                        <circle cx="18" cy="18" r="15.91" fill="none" stroke="#10b981" strokeWidth="3" strokeDasharray="50.9 100" strokeDashoffset="0" />
                        <circle cx="18" cy="18" r="15.91" fill="none" stroke="#f59e0b" strokeWidth="3" strokeDasharray="28.3 100" strokeDashoffset="-50.9" />
                        <circle cx="18" cy="18" r="15.91" fill="none" stroke="#f97316" strokeWidth="3" strokeDasharray="15.2 100" strokeDashoffset="-79.2" />
                        <circle cx="18" cy="18" r="15.91" fill="none" stroke="#ef4444" strokeWidth="3" strokeDasharray="5.6 100" strokeDashoffset="-94.4" />
                      </svg>
                      <div className="absolute text-center">
                        <div className="text-[9px] font-black text-slate-800 leading-none">1,243</div>
                        <div className="text-[6px] text-slate-400 uppercase mt-0.5">Total</div>
                      </div>
                    </div>
                    {/* Legend */}
                    <div className="flex-1 space-y-1 text-[7px]">
                      <div className="flex items-center justify-between">
                        <span className="flex items-center gap-1 text-slate-500">
                          <span className="size-1 rounded-full bg-[#10b981]" /> Low
                        </span>
                        <span className="font-semibold text-slate-800">632 (50.9%)</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="flex items-center gap-1 text-slate-500">
                          <span className="size-1 rounded-full bg-[#f59e0b]" /> Medium
                        </span>
                        <span className="font-semibold text-slate-800">352 (28.3%)</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="flex items-center gap-1 text-slate-500">
                          <span className="size-1 rounded-full bg-[#f97316]" /> High
                        </span>
                        <span className="font-semibold text-slate-800">189 (15.2%)</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="flex items-center gap-1 text-slate-500">
                          <span className="size-1 rounded-full bg-[#ef4444]" /> Critical
                        </span>
                        <span className="font-semibold text-slate-800">70 (5.6%)</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* 2 lists row */}
              <div className="grid grid-cols-2 gap-3">
                {/* Recent Documents */}
                <div className="bg-white border border-slate-200/80 p-3 rounded-lg flex flex-col justify-between">
                  <div>
                    <div className="text-[9px] font-bold text-slate-900">Recent Documents</div>
                    <div className="mt-2 space-y-1">
                      <div className="flex items-center justify-between p-1 border-b border-slate-50">
                        <span className="flex items-center gap-1 truncate max-w-[100px] text-slate-700">
                          <FileText className="size-2.5 text-slate-400" /> PO_2024_1058.pdf
                        </span>
                        <span className="text-[7px] text-emerald-600 bg-emerald-50 px-1 rounded border border-emerald-100 font-medium">Completed</span>
                      </div>
                      <div className="flex items-center justify-between p-1 border-b border-slate-50">
                        <span className="flex items-center gap-1 truncate max-w-[100px] text-slate-700">
                          <FileText className="size-2.5 text-slate-400" /> Invoice_QuickFix_1057.pdf
                        </span>
                        <span className="text-[7px] text-emerald-600 bg-emerald-50 px-1 rounded border border-emerald-100 font-medium">Completed</span>
                      </div>
                      <div className="flex items-center justify-between p-1">
                        <span className="flex items-center gap-1 truncate max-w-[100px] text-slate-700">
                          <FileText className="size-2.5 text-slate-400" /> Contract_Apex_1056.pdf
                        </span>
                        <span className="text-[7px] text-emerald-600 bg-emerald-50 px-1 rounded border border-emerald-100 font-medium">Completed</span>
                      </div>
                    </div>
                  </div>
                  <div className="text-[8px] text-[#f97316] font-semibold mt-2 hover:underline cursor-pointer">
                    View all documents &rarr;
                  </div>
                </div>

                {/* Top Vendors */}
                <div className="bg-white border border-slate-200/80 p-3 rounded-lg flex flex-col justify-between">
                  <div>
                    <div className="text-[9px] font-bold text-slate-900">Top Vendors by Spend</div>
                    <table className="w-full mt-2 text-[7px] text-left">
                      <thead>
                        <tr className="text-slate-400 border-b border-slate-100 font-medium">
                          <th className="pb-1">Vendor</th>
                          <th className="pb-1 text-right">Spend</th>
                          <th className="pb-1 text-center">Risk Score</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr className="border-b border-slate-50">
                          <td className="py-1 font-medium text-slate-700">QuickFix Facility Services</td>
                          <td className="py-1 text-right font-mono">$802,400</td>
                          <td className="py-1 text-center"><span className="px-1 py-0.5 rounded bg-amber-50 text-amber-600 font-medium">Medium</span></td>
                        </tr>
                        <tr className="border-b border-slate-50">
                          <td className="py-1 font-medium text-slate-700">Apex Industrial Supplies</td>
                          <td className="py-1 text-right font-mono">$320,100</td>
                          <td className="py-1 text-center"><span className="px-1 py-0.5 rounded bg-emerald-50 text-emerald-600 font-medium">Low</span></td>
                        </tr>
                        <tr className="border-b border-slate-50">
                          <td className="py-1 font-medium text-slate-700">Global Manufacturing LLC</td>
                          <td className="py-1 text-right font-mono">$145,230</td>
                          <td className="py-1 text-center"><span className="px-1 py-0.5 rounded bg-amber-50 text-amber-600 font-medium">Medium</span></td>
                        </tr>
                        <tr>
                          <td className="py-1 font-medium text-slate-700">Bright Logistics Ltd.</td>
                          <td className="py-1 text-right font-mono">$98,760</td>
                          <td className="py-1 text-center"><span className="px-1 py-0.5 rounded bg-emerald-50 text-emerald-600 font-medium">Low</span></td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                  <div className="text-[8px] text-[#f97316] font-semibold mt-2 hover:underline cursor-pointer">
                    View all vendors &rarr;
                  </div>
                </div>
              </div>

            </main>
          </div>
        </div>
      </section>

      {/* ── FOUR HORIZONTAL FEATURES SECTION ── */}
      <section id="features" className="border-t border-slate-100 bg-white py-16 px-6">
        <div className="mx-auto max-w-7xl grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
          
          {/* Card 1 */}
          <div className="flex flex-col items-start">
            <div className="size-11 rounded-xl bg-orange-50 border border-orange-100 flex items-center justify-center text-[#f97316] mb-4 shadow-sm">
              <FileText className="size-5.5 stroke-[2.2]" />
            </div>
            <h3 className="text-[17px] font-bold text-slate-900 mb-2">Intelligent Document Processing</h3>
            <p className="text-sm text-slate-500 leading-relaxed">
              OCR scanned documents and extract key entities with high-accuracy AI models.
            </p>
          </div>

          {/* Card 2 */}
          <div className="flex flex-col items-start">
            <div className="size-11 rounded-xl bg-orange-50 border border-orange-100 flex items-center justify-center text-[#f97316] mb-4 shadow-sm">
              <ShieldCheck className="size-5.5 stroke-[2.2]" />
            </div>
            <h3 className="text-[17px] font-bold text-slate-900 mb-2">Vendor Risk Prediction</h3>
            <p className="text-sm text-slate-500 leading-relaxed">
              ML-powered risk scoring using real supply chain data and advanced models.
            </p>
          </div>

          {/* Card 3 */}
          <div className="flex flex-col items-start">
            <div className="size-11 rounded-xl bg-orange-50 border border-orange-100 flex items-center justify-center text-[#f97316] mb-4 shadow-sm">
              <BarChart3 className="size-5.5 stroke-[2.2]" />
            </div>
            <h3 className="text-[17px] font-bold text-slate-900 mb-2">Advanced Analytics</h3>
            <p className="text-sm text-slate-500 leading-relaxed">
              Get real-time insights into spend, vendors, and risk distribution across your organization.
            </p>
          </div>

          {/* Card 4 */}
          <div className="flex flex-col items-start">
            <div className="size-11 rounded-xl bg-orange-50 border border-orange-100 flex items-center justify-center text-[#f97316] mb-4 shadow-sm">
              <Search className="size-5.5 stroke-[2.2]" />
            </div>
            <h3 className="text-[17px] font-bold text-slate-900 mb-2">RAG-Powered Search</h3>
            <p className="text-sm text-slate-500 leading-relaxed">
              Ask questions and get grounded answers from your entire document corpus.
            </p>
          </div>

        </div>
      </section>

      {/* ── HOW IT WORKS (FLOW STEPS) ── */}
      <section id="how-it-works" className="border-t border-slate-100 bg-slate-50/30 py-20 px-6">
        <div className="mx-auto max-w-7xl text-center">
          
          <div className="inline-flex items-center gap-1.5 text-xs font-bold text-[#f97316] uppercase tracking-wider mb-12">
            ✦ How SupplyMind Works ✦
          </div>

          {/* Flow Steps Row */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8 relative items-start">
            
            {/* Step 1 */}
            <div className="flex flex-col items-center group">
              <div className="size-14 rounded-2xl bg-white border border-slate-200/80 flex items-center justify-center text-[#f97316] mb-4 relative shadow-sm group-hover:border-orange-200 transition-colors">
                <Upload className="size-6 stroke-[2]" />
                <span className="absolute -bottom-1.5 -right-1.5 size-5 bg-[#f97316] text-white text-[10px] font-black rounded-full flex items-center justify-center border border-white">
                  1
                </span>
              </div>
              <h4 className="text-base font-bold text-slate-900 mb-1.5 mt-2">Ingest</h4>
              <p className="text-xs text-slate-500 leading-relaxed max-w-[200px]">
                Upload invoices, POs, contracts, and more.
              </p>
            </div>

            {/* Step 2 */}
            <div className="flex flex-col items-center group">
              <div className="size-14 rounded-2xl bg-white border border-slate-200/80 flex items-center justify-center text-[#f97316] mb-4 relative shadow-sm group-hover:border-orange-200 transition-colors">
                <Cpu className="size-6 stroke-[2]" />
                <span className="absolute -bottom-1.5 -right-1.5 size-5 bg-[#f97316] text-white text-[10px] font-black rounded-full flex items-center justify-center border border-white">
                  2
                </span>
              </div>
              <h4 className="text-base font-bold text-slate-900 mb-1.5 mt-2">Extract</h4>
              <p className="text-xs text-slate-500 leading-relaxed max-w-[200px]">
                AI extracts structured data and key entities.
              </p>
            </div>

            {/* Step 3 */}
            <div className="flex flex-col items-center group">
              <div className="size-14 rounded-2xl bg-white border border-slate-200/80 flex items-center justify-center text-[#f97316] mb-4 relative shadow-sm group-hover:border-orange-200 transition-colors">
                <ArrowRightLeft className="size-6 stroke-[2]" />
                <span className="absolute -bottom-1.5 -right-1.5 size-5 bg-[#f97316] text-white text-[10px] font-black rounded-full flex items-center justify-center border border-white">
                  3
                </span>
              </div>
              <h4 className="text-base font-bold text-slate-900 mb-1.5 mt-2">Analyze</h4>
              <p className="text-xs text-slate-500 leading-relaxed max-w-[200px]">
                ML models predict risk and calculate insights.
              </p>
            </div>

            {/* Step 4 */}
            <div className="flex flex-col items-center group">
              <div className="size-14 rounded-2xl bg-white border border-slate-200/80 flex items-center justify-center text-[#f97316] mb-4 relative shadow-sm group-hover:border-orange-200 transition-colors">
                <Brain className="size-6 stroke-[2]" />
                <span className="absolute -bottom-1.5 -right-1.5 size-5 bg-[#f97316] text-white text-[10px] font-black rounded-full flex items-center justify-center border border-white">
                  4
                </span>
              </div>
              <h4 className="text-base font-bold text-slate-900 mb-1.5 mt-2">Intelligence</h4>
              <p className="text-xs text-slate-500 leading-relaxed max-w-[200px]">
                Dashboards and RAG deliver actionable intelligence.
              </p>
            </div>

            {/* Horizontal flow line helpers (hidden on mobile) */}
            <div className="hidden md:block absolute top-7 left-[18%] w-[14%] border-t-2 border-dashed border-slate-200" />
            <div className="hidden md:block absolute top-7 left-[43%] w-[14%] border-t-2 border-dashed border-slate-200" />
            <div className="hidden md:block absolute top-7 left-[68%] w-[14%] border-t-2 border-dashed border-slate-200" />

          </div>
        </div>
      </section>

      {/* ── CALL TO ACTION BANNER ── */}
      <section className="bg-white py-16 px-6 border-t border-slate-100">
        <div className="mx-auto max-w-7xl bg-orange-50/50 border border-orange-100 rounded-3xl p-8 md:p-12 flex flex-col md:flex-row items-center justify-between gap-8 relative overflow-hidden">
          
          {/* Text content */}
          <div className="flex flex-col items-start text-left max-w-xl z-10">
            <h2 className="text-2xl md:text-3xl font-black text-slate-900 tracking-tight leading-snug mb-3">
              Ready to unlock intelligence from your procurement data?
            </h2>
            <p className="text-sm text-slate-500 leading-relaxed mb-6">
              Join procurement teams already using SupplyMind to reduce risk and maximize value.
            </p>
            <div className="flex flex-wrap items-center gap-3">
              <Link
                href="/dashboard"
                className="inline-flex h-11 items-center justify-center rounded-xl bg-[#f97316] px-5 text-sm font-semibold text-white hover:bg-[#ea580c] transition-colors gap-1 shadow-sm"
              >
                Launch Console <ArrowRight className="size-4" />
              </Link>
              <a
                href="http://127.0.0.1:8000/api/v1/docs"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex h-11 items-center justify-center rounded-xl border border-slate-200 bg-white px-5 text-sm font-semibold text-slate-600 hover:bg-slate-50 transition-colors gap-1.5"
              >
                Explore API Docs <ExternalLink className="size-3.5 text-slate-400" />
              </a>
            </div>
          </div>

          {/* Circular neural nodes background/graphic */}
          <div className="relative size-44 md:size-52 flex items-center justify-center z-10 shrink-0">
            <div className="absolute inset-0 rounded-full border border-orange-100/60 animate-[spin_60s_linear_infinite]" />
            <div className="absolute inset-4 rounded-full border border-dashed border-orange-200/50 animate-[spin_40s_linear_infinite_reverse]" />
            <div className="absolute inset-10 rounded-full border border-orange-200/40" />
            <div className="flex size-20 items-center justify-center rounded-full bg-white border border-orange-100 shadow-sm text-[#f97316]">
              <Brain className="size-10 stroke-[1.8] fill-orange-50/30" />
            </div>
          </div>
          
        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer className="border-t border-slate-100 bg-white py-12 px-6 text-sm text-slate-500">
        <div className="mx-auto max-w-7xl flex flex-col md:flex-row items-center justify-between gap-6">
          
          {/* Logo & copyright */}
          <div className="flex items-center gap-8">
            <div className="flex items-center gap-2">
              <div className="flex size-7 items-center justify-center rounded bg-[#f97316] text-white font-bold text-base shadow-sm">
                S
              </div>
              <span className="font-bold text-slate-900 text-base">SupplyMind</span>
            </div>
            <span>&copy; 2025 SupplyMind. All rights reserved.</span>
          </div>

          {/* Footer links */}
          <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
            <Link href="#product" className="hover:text-slate-900 transition-colors">Product</Link>
            <Link href="#features" className="hover:text-slate-900 transition-colors">Features</Link>
            <Link href="#how-it-works" className="hover:text-slate-900 transition-colors">How It Works</Link>
            <Link href="#pricing" className="hover:text-slate-900 transition-colors">Pricing</Link>
            <a href="http://127.0.0.1:8000/api/v1/docs" target="_blank" rel="noopener noreferrer" className="hover:text-slate-900 transition-colors">Docs</a>
            <a href="http://127.0.0.1:8000/api/v1/docs" target="_blank" rel="noopener noreferrer" className="hover:text-slate-900 transition-colors">API Docs</a>
          </div>

        </div>
      </footer>

    </div>
  );
}

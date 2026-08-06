"use client";

import { Search, Bell, Sparkles, ShieldCheck } from "lucide-react";
import { useState } from "react";

interface HeaderProps {
  title?: string;
  subtitle?: string;
}

export function Header({ title, subtitle }: HeaderProps) {
  const [searchQuery, setSearchQuery] = useState("");

  return (
    <header className="sticky top-0 z-30 h-20 flex items-center justify-between px-6 lg:px-8 bg-[#070a11]/90 backdrop-blur-xl border-b border-slate-800/80 transition-all duration-300">
      {/* Page title */}
      <div>
        {title && (
          <h1 className="text-xl lg:text-2xl font-extrabold font-heading text-slate-100 tracking-tight flex items-center gap-2">
            {title}
          </h1>
        )}
        {subtitle && (
          <p className="text-xs text-slate-400 mt-0.5 font-medium">{subtitle}</p>
        )}
      </div>

      {/* Right side: Search + System Status */}
      <div className="flex items-center gap-4">
        <div className="hidden xl:flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold">
          <ShieldCheck className="w-3.5 h-3.5" />
          <span>ENTERPRISE RAG ACTIVE</span>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search contracts, clauses, or legislation..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-64 lg:w-80 pl-10 pr-4 py-2 text-xs rounded-xl bg-slate-900/90 text-slate-100 placeholder:text-slate-500 focus:bg-slate-900 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 border border-slate-800 transition-all duration-300"
          />
        </div>

        {/* Notifications */}
        <button className="relative p-2.5 rounded-xl bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-300 transition-all duration-300">
          <Bell className="w-4 h-4 text-emerald-400" />
          <span className="absolute top-2 right-2 w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
        </button>
      </div>
    </header>
  );
}

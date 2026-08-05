"use client";

/**
 * Dashboard header with search and user actions.
 */

import { Search, Bell } from "lucide-react";
import { useState } from "react";

interface HeaderProps {
  title?: string;
  subtitle?: string;
}

export function Header({ title, subtitle }: HeaderProps) {
  const [searchQuery, setSearchQuery] = useState("");

  return (
    <header className="sticky top-0 z-30 h-16 flex items-center justify-between px-8 border-b border-[var(--border-primary)] glass-strong">
      {/* Page title */}
      <div>
        {title && <h1 className="text-lg font-semibold">{title}</h1>}
        {subtitle && (
          <p className="text-sm text-[var(--text-muted)]">{subtitle}</p>
        )}
      </div>

      {/* Right side: Search + Notifications */}
      <div className="flex items-center gap-4">
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-muted)]" />
          <input
            type="text"
            placeholder="Search documents..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-64 pl-10 pr-4 py-2 text-sm rounded-xl bg-[var(--bg-surface)] border border-[var(--border-primary)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500/50 transition-all"
          />
        </div>

        {/* Notifications */}
        <button className="relative p-2 rounded-xl hover:bg-white/5 transition-colors">
          <Bell className="w-5 h-5 text-[var(--text-secondary)]" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-blue-500" />
        </button>
      </div>
    </header>
  );
}

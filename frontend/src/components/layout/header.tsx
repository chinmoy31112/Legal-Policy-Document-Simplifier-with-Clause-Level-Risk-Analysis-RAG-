"use client";

import * as React from "react";
import Link from "next/link";
import { Menu, UploadCloud } from "lucide-react";
import { useLayout } from "./layout-context";

interface HeaderProps {
  title?: string;
  subtitle?: string;
}

export function Header({ title, subtitle }: HeaderProps) {
  const { toggleMobileNav } = useLayout();

  return (
    <header className="sticky top-0 z-10 h-16 flex items-center justify-between px-4 lg:px-6 bg-[var(--card)]/90 backdrop-blur-md border-b border-[var(--border)] shrink-0 transition-colors">
      {/* Left: Mobile Menu Trigger + Title */}
      <div className="flex items-center gap-3 min-w-0">
        <button
          type="button"
          onClick={toggleMobileNav}
          aria-label="Open navigation menu"
          className="md:hidden p-2 rounded-[10px] text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-[var(--soft-surface)] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
        >
          <Menu className="h-5 w-5" />
        </button>

        <div className="min-w-0">
          {title && (
            <h1 className="text-base lg:text-lg font-serif font-semibold text-[var(--foreground)] tracking-tight truncate">
              {title}
            </h1>
          )}
          {subtitle && (
            <p className="text-[11px] text-[var(--muted-foreground)] truncate hidden sm:block">
              {subtitle}
            </p>
          )}
        </div>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-2.5 shrink-0">
        {/* Status Pill */}
        <div
          className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[var(--risk-standard-bg)] border border-[var(--risk-standard-border)] text-[var(--risk-standard-text)] text-[11px] font-medium"
          aria-label="System status: Gemini RAG Active"
        >
          <span className="w-1.5 h-1.5 rounded-full bg-[var(--risk-standard-text)] animate-pulse" />
          <span>Gemini RAG Active</span>
        </div>

        {/* Quick CTA */}
        <Link
          href="/upload"
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-[var(--accent-foreground)] rounded-[10px] bg-[var(--accent)] hover:opacity-90 active:scale-[0.98] transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-1"
        >
          <UploadCloud className="w-3.5 h-3.5" />
          <span className="hidden xs:inline">Analyze</span>
          <span>Contract</span>
        </Link>
      </div>
    </header>
  );
}

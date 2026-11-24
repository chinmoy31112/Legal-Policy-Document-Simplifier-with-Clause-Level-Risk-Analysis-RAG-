"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  UploadCloud,
  BookOpen,
  ShieldCheck,
  History,
  Settings,
  LogOut,
  X,
  FileText,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/providers/auth-provider";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { useLayout } from "./layout-context";

export const NAVIGATION_ITEMS = [
  {
    name: "Upload",
    href: "/upload",
    icon: UploadCloud,
    description: "Upload and analyze contracts",
  },
  {
    name: "Knowledge Base",
    href: "/documents?tab=kb",
    icon: BookOpen,
    description: "Standard clauses & benchmarks",
  },
  {
    name: "Analysis",
    href: "/analysis",
    icon: ShieldCheck,
    description: "Interactive clause risk review",
  },
  {
    name: "History",
    href: "/documents",
    icon: History,
    description: "Past analyses & document archive",
  },
  {
    name: "Settings",
    href: "/settings",
    icon: Settings,
    description: "Preferences and GDPR data rights",
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const { isMobileNavOpen, closeMobileNav } = useLayout();

  // Close mobile nav on route change
  React.useEffect(() => {
    closeMobileNav();
  }, [pathname, closeMobileNav]);

  // Close on Escape key when mobile nav is open
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isMobileNavOpen) {
        closeMobileNav();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isMobileNavOpen, closeMobileNav]);

  const navContent = (
    <div className="flex flex-col h-full w-[224px] bg-[var(--card)] text-[var(--foreground)] border-r border-[var(--border)] select-none">
      {/* Brand Header */}
      <div className="flex h-16 shrink-0 items-center justify-between px-4 border-b border-[var(--border)] bg-[var(--card)]">
        <Link
          href="/dashboard"
          className="flex items-center gap-2.5 group focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] rounded-[10px] p-1"
          aria-label="LegalLens AI Home"
        >
          <div className="w-8 h-8 rounded-[10px] bg-[var(--accent)] flex items-center justify-center text-[var(--accent-foreground)] shadow-xs transition-transform duration-150 group-hover:scale-105">
            <FileText className="h-4 w-4" />
          </div>
          <div className="flex flex-col">
            <span className="font-serif text-base font-semibold tracking-tight leading-none text-[var(--foreground)]">
              LegalLens
            </span>
            <span className="text-[10px] font-medium text-[var(--muted-foreground)] tracking-wide mt-0.5">
              Policy & Clause AI
            </span>
          </div>
        </Link>

        {/* Mobile close button */}
        <button
          type="button"
          onClick={closeMobileNav}
          aria-label="Close navigation menu"
          className="md:hidden p-1.5 rounded-[10px] text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-[var(--soft-surface)] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Main Nav Links */}
      <div className="flex-1 overflow-y-auto px-2.5 py-4 space-y-1">
        <div className="px-2 pb-1.5 text-[10px] font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
          Navigation
        </div>
        <nav className="space-y-1" aria-label="Main Navigation">
          {NAVIGATION_ITEMS.map((item) => {
            const isBaseDocuments = item.href === "/documents";
            const isKbTab = item.href === "/documents?tab=kb";

            let isActive = false;
            if (isKbTab) {
              isActive = pathname === "/documents";
            } else if (isBaseDocuments) {
              isActive = pathname === "/documents";
            } else {
              isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);
            }

            return (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  "group flex items-center gap-2.5 rounded-[10px] px-3 py-2 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-1",
                  isActive
                    ? "bg-[var(--soft-surface)] text-[var(--accent)] font-semibold border border-[var(--border)]"
                    : "text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-[var(--soft-surface)]/60"
                )}
                aria-current={isActive ? "page" : undefined}
              >
                <item.icon
                  className={cn(
                    "h-4 w-4 shrink-0 transition-transform duration-150",
                    isActive ? "text-[var(--accent)]" : "text-[var(--muted-foreground)] group-hover:text-[var(--foreground)]"
                  )}
                  aria-hidden="true"
                />
                <span className="truncate">{item.name}</span>
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Sidebar Footer: Theme Toggle & User Info */}
      <div className="p-3 border-t border-[var(--border)] bg-[var(--soft-surface)]/40 shrink-0 space-y-2.5">
        {/* Theme Switcher */}
        <div className="flex items-center justify-between px-1">
          <span className="text-[11px] font-medium text-[var(--muted-foreground)]">Theme</span>
          <ThemeToggle />
        </div>

        {/* User Card */}
        <div className="flex items-center justify-between p-2 rounded-[10px] bg-[var(--card)] border border-[var(--border)]">
          <div className="min-w-0 pr-2">
            <p className="text-xs font-medium text-[var(--foreground)] truncate">
              {user?.full_name || "Legal Reviewer"}
            </p>
            <p className="text-[10px] text-[var(--muted-foreground)] truncate">
              {user?.email || "reviewer@firm.internal"}
            </p>
          </div>
          <button
            type="button"
            onClick={logout}
            aria-label="Log out of application"
            title="Log out"
            className="p-1.5 rounded-[8px] text-[var(--muted-foreground)] hover:text-[var(--risk-high-text)] hover:bg-[var(--risk-high-bg)] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] shrink-0"
          >
            <LogOut className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop Sidebar (Fixed 224px) */}
      <aside
        className="hidden md:flex h-full w-[224px] shrink-0 z-20"
        aria-label="Desktop Sidebar"
      >
        {navContent}
      </aside>

      {/* Mobile Drawer (Accessible modal with slide-in animation) */}
      {isMobileNavOpen && (
        <div
          className="fixed inset-0 z-50 md:hidden flex"
          role="dialog"
          aria-modal="true"
          aria-label="Mobile Navigation Drawer"
        >
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/50 backdrop-blur-xs transition-opacity animate-in fade-in duration-200"
            onClick={closeMobileNav}
            aria-hidden="true"
          />

          {/* Drawer Content */}
          <div className="relative z-50 flex h-full w-[224px] flex-col shadow-2xl animate-in slide-in-from-left duration-200">
            {navContent}
          </div>
        </div>
      )}
    </>
  );
}

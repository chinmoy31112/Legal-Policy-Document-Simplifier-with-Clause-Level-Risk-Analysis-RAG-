"use client";

import * as React from "react";
import { ClauseAnalysis } from "@/types/analysis";
import { Document } from "@/types/document";
import { Search, FileText } from "lucide-react";
import { RiskChip } from "@/components/ui/risk-chip";
import {
  computeClauseCounts,
  getClauseBucket,
  type FilterBucket,
} from "@/lib/clause-stats";

interface DocumentViewerProps {
  document: Document;
  clauses: ClauseAnalysis[];
  activeClauseId: string | null;
  onClauseSelect: (id: string) => void;
  className?: string;
}

export function DocumentViewer({
  document,
  clauses,
  activeClauseId,
  onClauseSelect,
  className = "",
}: DocumentViewerProps) {
  const [search, setSearch] = React.useState("");
  const [categoryFilter, setCategoryFilter] = React.useState<FilterBucket>("all");

  const documentText =
    document.raw_text ||
    clauses.map((c) => c.clause?.content || c.plain_english_summary).join("\n\n");

  const counts = React.useMemo(() => computeClauseCounts(clauses), [clauses]);

  const filteredClauses = React.useMemo(() => {
    return clauses.filter((analysis) => {
      if (categoryFilter !== "all") {
        if (getClauseBucket(analysis.risk_category) !== categoryFilter) {
          return false;
        }
      }

      if (search.trim()) {
        const q = search.toLowerCase();
        const content = (analysis.clause?.content || "").toLowerCase();
        const summary = (analysis.plain_english_summary || "").toLowerCase();
        const title = (analysis.clause?.title || "").toLowerCase();
        return content.includes(q) || summary.includes(q) || title.includes(q);
      }

      return true;
    });
  }, [clauses, search, categoryFilter]);

  return (
    <div
      className={`flex flex-col h-full rounded-[18px] border border-[var(--border)] bg-[var(--card)] overflow-hidden shadow-none ${className}`}
      data-testid="document-viewer"
    >
      {/* Viewer Toolbar */}
      <div className="p-3.5 border-b border-[var(--border)] bg-[var(--soft-surface)]/60 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2.5 shrink-0">
        {/* Search Input */}
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-[var(--muted-foreground)] pointer-events-none" />
          <input
            type="text"
            placeholder="Search agreement clauses..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full h-9 pl-9 pr-3 rounded-[10px] bg-[var(--card)] border border-[var(--border)] text-xs text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
            aria-label="Search within agreement text"
          />
        </div>

        {/* Category Filter Pills using single clause count source */}
        <div
          className="flex items-center gap-1 overflow-x-auto pb-1 sm:pb-0"
          role="group"
          aria-label="Filter clauses by severity"
        >
          <button
            type="button"
            data-testid="filter-all"
            onClick={() => setCategoryFilter("all")}
            className={`px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors ${
              categoryFilter === "all"
                ? "bg-[var(--accent)] text-[var(--accent-foreground)]"
                : "bg-[var(--card)] text-[var(--muted-foreground)] border border-[var(--border)] hover:bg-[var(--soft-surface)]"
            }`}
          >
            All ({counts.filterCounts.all})
          </button>
          <button
            type="button"
            data-testid="filter-high"
            onClick={() => setCategoryFilter("high")}
            className={`px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors ${
              categoryFilter === "high"
                ? "bg-[var(--risk-high-text)] text-white"
                : "bg-[var(--card)] text-[var(--muted-foreground)] border border-[var(--border)] hover:bg-[var(--soft-surface)]"
            }`}
          >
            High Risk ({counts.filterCounts.high})
          </button>
          <button
            type="button"
            data-testid="filter-medium"
            onClick={() => setCategoryFilter("medium")}
            className={`px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors ${
              categoryFilter === "medium"
                ? "bg-[var(--risk-unusual-text)] text-white"
                : "bg-[var(--card)] text-[var(--muted-foreground)] border border-[var(--border)] hover:bg-[var(--soft-surface)]"
            }`}
          >
            Medium ({counts.filterCounts.medium})
          </button>
          <button
            type="button"
            data-testid="filter-standard"
            onClick={() => setCategoryFilter("standard")}
            className={`px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors ${
              categoryFilter === "standard"
                ? "bg-[var(--risk-standard-text)] text-white"
                : "bg-[var(--card)] text-[var(--muted-foreground)] border border-[var(--border)] hover:bg-[var(--soft-surface)]"
            }`}
          >
            Standard ({counts.filterCounts.standard})
          </button>
        </div>
      </div>

      {/* Document Canvas */}
      <div className="flex-1 overflow-y-auto bg-white text-[#1A1A1A] p-5 sm:p-7 select-text pdf-canvas-container">
        {/* Paper Title / Header */}
        <div className="border-b border-[#E5E0D8] pb-3 mb-5">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[#736B5E] mb-1">
            <FileText className="w-3.5 h-3.5 text-[#B4532A]" />
            <span>{document.document_type.replace(/_/g, " ")}</span>
          </div>
          <h2 className="font-serif text-lg sm:text-xl font-bold text-[#1A1A1A] leading-tight">
            {document.original_filename}
          </h2>
        </div>

        {/* Clause Overlays */}
        {filteredClauses.length === 0 ? (
          <div className="text-center py-12 text-sm text-[#736B5E]">
            {clauses.length === 0 ? (
              <p className="whitespace-pre-wrap font-serif text-xs leading-relaxed text-[#2B2622]">
                {documentText}
              </p>
            ) : (
              <p>No clauses match your search query or filter.</p>
            )}
          </div>
        ) : (
          <div className="space-y-3" data-testid="clause-list">
            {filteredClauses.map((analysis) => {
              const isSelected = activeClauseId === analysis.id;
              const cat = String(analysis.risk_category || "").toLowerCase();

              let overlayStyles =
                "border-l-4 rounded-r-[8px] p-3 transition-all cursor-pointer ";

              if (
                cat === "high" ||
                cat === "high_risk" ||
                cat === "critical" ||
                cat === "potentially_unenforceable"
              ) {
                overlayStyles += isSelected
                  ? "bg-[#FAD7D7] border-l-[#8F1D1D] ring-2 ring-[#8F1D1D] "
                  : "bg-[#FAD7D7]/40 border-l-[#8F1D1D] hover:bg-[#FAD7D7]/70 ";
              } else if (cat === "one_sided") {
                overlayStyles += isSelected
                  ? "bg-[#FDE3CF] border-l-[#8A3B00] ring-2 ring-[#8A3B00] "
                  : "bg-[#FDE3CF]/40 border-l-[#8A3B00] hover:bg-[#FDE3CF]/70 ";
              } else if (
                cat === "slightly_unusual" ||
                cat === "medium" ||
                cat === "unusual"
              ) {
                overlayStyles += isSelected
                  ? "bg-[#FBF0C8] border-l-[#6B4F00] ring-2 ring-[#6B4F00] "
                  : "bg-[#FBF0C8]/40 border-l-[#6B4F00] hover:bg-[#FBF0C8]/70 ";
              } else {
                overlayStyles += isSelected
                  ? "bg-[#E3F1E4] border-l-[#1F5C2E] ring-2 ring-[#1F5C2E] "
                  : "bg-[#E3F1E4]/40 border-l-[#1F5C2E] hover:bg-[#E3F1E4]/70 ";
              }

              if (isSelected) {
                overlayStyles += "shadow-sm ";
              }

              const rawNumber = analysis.clause?.clause_number?.trim() || "";
              const title = analysis.clause?.title?.trim() || "Contract Clause";

              let displayHeader = title;
              if (rawNumber) {
                if (
                  !displayHeader.startsWith(rawNumber) &&
                  !/^\d+[\.\)]/.test(displayHeader)
                ) {
                  displayHeader = `${rawNumber} ${displayHeader}`;
                }
              } else if (analysis.clause?.clause_index !== undefined) {
                const fallbackPrefix = `§ ${analysis.clause.clause_index + 1}`;
                if (!/^\d+[\.\)]/.test(displayHeader)) {
                  displayHeader = `${fallbackPrefix} ${displayHeader}`;
                }
              }

              return (
                <div
                  key={analysis.id}
                  id={`clause-${analysis.id}`}
                  data-testid="clause-item"
                  onClick={() => onClauseSelect(analysis.id)}
                  className={overlayStyles}
                  tabIndex={0}
                  role="button"
                  aria-pressed={isSelected}
                  aria-label={`Clause: ${displayHeader}`}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      onClauseSelect(analysis.id);
                    }
                  }}
                >
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className="font-serif text-xs font-semibold text-[#1A1A1A] line-clamp-1">
                      {displayHeader}
                    </span>
                    <RiskChip
                      category={analysis.risk_category}
                      score={analysis.risk_score}
                      size="sm"
                    />
                  </div>
                  <p className="font-serif text-xs text-[#2B2622] leading-relaxed whitespace-pre-wrap text-justify [text-align:justify]">
                    {analysis.clause?.content || analysis.plain_english_summary}
                  </p>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

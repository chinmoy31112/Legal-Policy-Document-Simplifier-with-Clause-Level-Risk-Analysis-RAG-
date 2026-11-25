"use client";

import * as React from "react";
import { ClauseAnalysis } from "@/types/analysis";
import { RiskChip } from "@/components/ui/risk-chip";
import {
  FileText,
  AlertTriangle,
  Scale,
  Sparkles,
  ChevronDown,
  ChevronUp,
  X,
  FileSearch,
  Copy,
  Check,
} from "lucide-react";

interface ClauseDetailPanelProps {
  clause: ClauseAnalysis | null;
  onClose?: () => void;
  className?: string;
}

export function ClauseDetailPanel({
  clause,
  onClose,
  className = "",
}: ClauseDetailPanelProps) {
  const [detailsExpanded, setDetailsExpanded] = React.useState(false);
  const [copied, setCopied] = React.useState(false);

  const handleCopyRewrite = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!clause) {
    return (
      <div
        className={`flex flex-col items-center justify-center p-8 text-center h-full rounded-[18px] border border-[var(--border)] bg-[var(--card)] text-[var(--muted-foreground)] ${className}`}
        data-testid="clause-detail-empty"
      >
        <div className="w-12 h-12 rounded-[14px] bg-[var(--soft-surface)] flex items-center justify-center mb-3 text-[var(--accent)]">
          <FileSearch className="w-6 h-6" />
        </div>
        <h4 className="font-serif text-sm font-semibold text-[var(--foreground)] mb-1">
          No Clause Selected
        </h4>
        <p className="text-xs text-[var(--muted-foreground)] max-w-xs leading-relaxed">
          Select any clause in the agreement viewer on the left to view in-depth risk analysis, benchmark precedents, and suggested rewrites.
        </p>
      </div>
    );
  }

  const clauseNumber =
    clause.clause?.clause_number ||
    (clause.clause?.clause_index !== undefined ? `Clause ${clause.clause.clause_index + 1}` : "Clause");

  return (
    <div
      className={`flex flex-col h-full rounded-[18px] border border-[var(--border)] bg-[var(--card)] text-[var(--foreground)] overflow-hidden shadow-none ${className}`}
      data-testid="clause-detail-panel"
      id={`card-${clause.id}`}
    >
      {/* Header */}
      <div className="p-4 sm:p-5 border-b border-[var(--border)] bg-[var(--soft-surface)]/40 shrink-0">
        <div className="flex items-center justify-between gap-2 mb-2">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[11px] font-semibold text-[var(--muted-foreground)] px-2.5 py-0.5 rounded-[8px] bg-[var(--card)] border border-[var(--border)]">
              {clauseNumber}
            </span>
            <RiskChip
              category={clause.risk_category}
              score={clause.risk_score}
              size="sm"
            />
          </div>
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              aria-label="Close clause details"
              className="p-1 rounded-[8px] text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-[var(--soft-surface)] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        <h3 className="font-serif text-base font-semibold text-[var(--foreground)] tracking-tight">
          {clause.clause?.title || "Legal Provision"}
        </h3>
      </div>

      {/* Scrollable Content Body */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-4">
        {/* Plain English Summary */}
        <div className="space-y-1.5">
          <h4 className="text-[11px] font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
            Plain English Summary
          </h4>
          <div className="p-3.5 rounded-[10px] bg-[var(--soft-surface)] border border-[var(--border)] text-xs text-[var(--foreground)] leading-relaxed">
            {clause.plain_english_summary}
          </div>
        </div>

        {/* Key Risk Factors */}
        {clause.risk_reasons && clause.risk_reasons.length > 0 && (
          <div className="space-y-1.5">
            <h4 className="text-[11px] font-semibold uppercase tracking-wider text-[var(--risk-high-text)] flex items-center gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
              <span>Flagged</span>
            </h4>
            <div className="p-3.5 rounded-[10px] bg-[var(--risk-high-bg)] border border-[var(--risk-high-border)] text-xs text-[var(--risk-high-text)]">
              <ul className="space-y-1.5 list-disc list-inside">
                {clause.risk_reasons.map((reason, i) => (
                  <li key={i} className="leading-relaxed">
                    <span>{reason}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {/* Suggested Balanced Rewrite */}
        {clause.suggested_rewrite && (
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <h4 className="text-[11px] font-semibold uppercase tracking-wider text-[var(--accent)] flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 shrink-0" />
                <span>Suggested Balanced Rewrite</span>
              </h4>
              <button
                type="button"
                onClick={() => handleCopyRewrite(clause.suggested_rewrite!)}
                aria-label="Copy suggested rewrite"
                className="inline-flex items-center gap-1 text-[11px] font-medium text-[var(--muted-foreground)] hover:text-[var(--accent)] px-2 py-0.5 rounded-[6px] transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--accent)]"
              >
                {copied ? (
                  <>
                    <Check className="w-3 h-3 text-[var(--risk-standard-text)]" />
                    <span className="text-[var(--risk-standard-text)]">Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3 h-3" />
                    <span>Copy</span>
                  </>
                )}
              </button>
            </div>
            <div className="p-3.5 rounded-[10px] bg-[var(--card)] border border-[var(--border)] text-xs text-[var(--foreground)] leading-relaxed italic border-l-3 border-l-[var(--accent)]">
              &ldquo;{clause.suggested_rewrite}&rdquo;
            </div>
          </div>
        )}

        {/* Expandable Details (Original text, missing protections, legal concerns) */}
        <div className="pt-2 border-t border-[var(--border)]">
          <button
            type="button"
            onClick={() => setDetailsExpanded(!detailsExpanded)}
            className="w-full flex items-center justify-between py-2 text-xs font-medium text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--accent)] rounded-[8px]"
          >
            <span>{detailsExpanded ? "Hide" : "Show"} Verbatim & Advanced Details</span>
            {detailsExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>

          {detailsExpanded && (
            <div className="space-y-3.5 pt-2 animate-in fade-in duration-150">
              {/* Original Verbatim Text */}
              {clause.clause?.content && (
                <div className="space-y-1">
                  <h5 className="text-[10px] font-semibold uppercase tracking-wider text-[var(--muted-foreground)] flex items-center gap-1">
                    <FileText className="w-3 h-3" />
                    <span>Original Contract Text</span>
                  </h5>
                  <div className="p-3 rounded-[10px] bg-[var(--soft-surface)] border border-[var(--border)] text-[11px] font-mono leading-relaxed text-[var(--foreground)] whitespace-pre-wrap">
                    {clause.clause.content}
                  </div>
                </div>
              )}

              {/* Missing Reciprocal Protections */}
              {clause.missing_protections && clause.missing_protections.length > 0 && (
                <div className="space-y-1">
                  <h5 className="text-[10px] font-semibold uppercase tracking-wider text-[var(--risk-onesided-text)] flex items-center gap-1">
                    <Scale className="w-3 h-3" />
                    <span>Missing Reciprocal Protections</span>
                  </h5>
                  <div className="p-3 rounded-[10px] bg-[var(--risk-onesided-bg)] border border-[var(--risk-onesided-border)] text-[11px] text-[var(--risk-onesided-text)]">
                    <ul className="space-y-1 list-disc list-inside">
                      {clause.missing_protections.map((prot, i) => (
                        <li key={i}>{prot}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}

              {/* Potential Legal Concern */}
              {clause.potential_legal_concern && (
                <div className="space-y-1">
                  <h5 className="text-[10px] font-semibold uppercase tracking-wider text-[var(--risk-high-text)] flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3" />
                    <span>Enforceability / Statutory Concern</span>
                  </h5>
                  <div className="p-3 rounded-[10px] bg-[var(--risk-high-bg)] border border-[var(--risk-high-border)] text-[11px] text-[var(--risk-high-text)] leading-relaxed">
                    {clause.potential_legal_concern}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

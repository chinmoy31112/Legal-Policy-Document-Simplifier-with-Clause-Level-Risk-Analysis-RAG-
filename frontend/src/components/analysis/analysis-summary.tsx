"use client";

import * as React from "react";
import { ClauseAnalysis, DocumentAnalysis } from "@/types/analysis";
import { FileDown, FileJson, FileText } from "lucide-react";
import { API_BASE_URL } from "@/lib/constants";
import { RiskChip } from "@/components/ui/risk-chip";
import { Button } from "@/components/ui/button";
import { pluralize } from "@/lib/utils";
import { computeClauseCounts } from "@/lib/clause-stats";

interface AnalysisSummaryProps {
  analysis: DocumentAnalysis;
  documentId?: string;
  clauses?: ClauseAnalysis[] | null;
  clauseCount?: number;
  isProvisional?: boolean;
  className?: string;
}

export function AnalysisSummary({
  analysis,
  documentId,
  clauses,
  clauseCount,
  isProvisional = false,
  className = "",
}: AnalysisSummaryProps) {
  const score = analysis.overall_risk_score;
  const isNonLegal =
    score === null ||
    score === undefined ||
    (analysis.overall_summary &&
      analysis.overall_summary.toLowerCase().includes("doesn't look like a legal"));

  if (isNonLegal) {
    return (
      <div
        className={`p-6 rounded-[18px] border border-[var(--border)] bg-[var(--card)] flex flex-col md:flex-row items-start md:items-center justify-between gap-6 select-none ${className}`}
      >
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-[14px] bg-[var(--soft-surface)] border border-[var(--border)] flex items-center justify-center shrink-0 text-[var(--accent)]">
            <FileText className="w-7 h-7" />
          </div>
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-semibold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-[var(--soft-surface)] text-[var(--muted-foreground)] border border-[var(--border)]">
                Intake Classification
              </span>
            </div>
            <h3 className="font-serif text-base font-semibold text-[var(--foreground)]">
              This doesn&apos;t look like a legal or policy document
            </h3>
            <p className="text-xs text-[var(--muted-foreground)] leading-relaxed max-w-xl">
              {analysis.overall_summary ||
                "The uploaded file appears to be a setup guide, user manual, or technical documentation rather than a binding legal agreement. Clause risk scoring and precedent benchmarking were skipped."}
            </p>
          </div>
        </div>
      </div>
    );
  }

  let overallCategory = "standard";
  if (score !== null && score !== undefined) {
    if (score >= 75) {
      overallCategory = "high_risk";
    } else if (score >= 50) {
      overallCategory = "one_sided";
    } else if (score >= 25) {
      overallCategory = "slightly_unusual";
    }
  }

  const counts = computeClauseCounts(clauses, analysis.risk_distribution);
  const totalEvaluated = counts.total || clauseCount || 0;
  const showProvisional =
    isProvisional ||
    Boolean(analysis.is_provisional) ||
    Boolean(
      analysis.overall_summary &&
        analysis.overall_summary.includes("Finalizing summary")
    );

  const segments = [
    {
      key: "standard",
      label: "Standard",
      count: counts.standard,
      colorClass: "bg-[var(--risk-standard-text)]",
    },
    {
      key: "slightly_unusual",
      label: "Slightly Unusual",
      count: counts.slightlyUnusual,
      colorClass: "bg-[var(--risk-unusual-text)]",
    },
    {
      key: "one_sided",
      label: "One-Sided",
      count: counts.oneSided,
      colorClass: "bg-[var(--risk-onesided-text)]",
    },
    {
      key: "high_risk",
      label: "High Risk",
      count: counts.highRisk + counts.unenforceable,
      colorClass: "bg-[var(--risk-high-text)]",
    },
  ].filter((seg) => seg.count > 0);

  const handleDownload = (format: "json" | "markdown" | "pdf") => {
    const docId = documentId || analysis.document_id;
    if (!docId) return;
    const url = `${API_BASE_URL}/documents/${docId}/export/${format}`;
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;

    fetch(url, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then((res) => {
        if (!res.ok) throw new Error("Export download failed");
        return res.blob();
      })
      .then((blob) => {
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = downloadUrl;
        const ext = format === "json" ? "json" : format === "pdf" ? "pdf" : "md";
        a.download = `risk_analysis_export.${ext}`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(downloadUrl);
      })
      .catch((err) => console.error("Export download failed:", err));
  };

  return (
    <div className={`space-y-4 select-none ${className}`} data-testid="analysis-summary">
      {/* Main Overall Risk Card */}
      <div className="p-5 sm:p-6 rounded-[18px] border border-[var(--border)] bg-[var(--card)] space-y-3.5">
        {/* Top Alignment Bar: Badges on left, Download Options in-line on right */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-1 border-b border-[var(--border)]/30">
          <div className="flex flex-wrap items-center gap-2.5">
            <RiskChip category={overallCategory} size="sm" />
            {showProvisional && (
              <span
                data-testid="provisional-score-badge"
                className="text-[10px] font-semibold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-amber-500/15 text-amber-400 border border-amber-500/30 animate-pulse"
              >
                Provisional
              </span>
            )}
            <span
              data-testid="summary-clause-count"
              className="text-xs text-[var(--muted-foreground)] font-medium"
            >
              {pluralize(totalEvaluated, "clause")} evaluated
            </span>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleDownload("pdf")}
              className="h-8 text-xs bg-[var(--soft-surface)]/80 hover:bg-[var(--accent)] hover:text-white border-[var(--border)] transition-colors whitespace-nowrap"
              title="Download full analysis report as PDF"
            >
              <FileDown className="w-3.5 h-3.5 mr-1" />
              <span>Export PDF</span>
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleDownload("markdown")}
              className="h-8 text-xs bg-[var(--soft-surface)]/80 hover:bg-[var(--accent)] hover:text-white border-[var(--border)] transition-colors whitespace-nowrap"
            >
              <FileText className="w-3.5 h-3.5 mr-1" />
              <span>Export Markdown</span>
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleDownload("json")}
              className="h-8 text-xs bg-[var(--soft-surface)]/80 hover:bg-[var(--accent)] hover:text-white border-[var(--border)] transition-colors whitespace-nowrap"
            >
              <FileJson className="w-3.5 h-3.5 mr-1" />
              <span>Export JSON</span>
            </Button>
          </div>
        </div>

        {/* Content Row: Score Pillar & Justified Executive Summary Text */}
        <div className="flex items-start gap-4 pt-1">
          <div className="w-20 h-20 rounded-[14px] bg-[var(--soft-surface)] border border-[var(--border)] flex flex-col items-center justify-center shrink-0">
            <span
              data-testid="overall-risk-score"
              className="font-serif text-3xl font-bold text-[var(--foreground)] tabular-nums leading-none"
            >
              {score}
            </span>
            <span className="text-[9px] font-semibold uppercase tracking-wider text-[var(--muted-foreground)] mt-1 text-center px-1">
              {showProvisional ? "Provisional" : "Risk Score"}
            </span>
          </div>

          <p className="text-xs text-[var(--foreground)] leading-relaxed flex-1 text-justify [text-align:justify] [text-justify:inter-word]">
            {analysis.overall_summary ||
              "Contract clause risk analysis evaluated with sequential grounding against standard commercial precedents."}
          </p>
        </div>

        {/* Multi-segment Risk Breakdown Bar (driven from the same clause counts as filters) */}
        {totalEvaluated > 0 && segments.length > 0 && (
          <div className="pt-2 space-y-1.5" data-testid="risk-breakdown-container">
            <div
              data-testid="risk-breakdown-bar"
              className="h-2 w-full bg-[var(--soft-surface)] rounded-full overflow-hidden flex gap-0.5 border border-[var(--border)]"
              role="img"
              aria-label={`Clause risk distribution across ${pluralize(totalEvaluated, "clause")}`}
            >
              {segments.map((seg) => (
                <div
                  key={seg.key}
                  data-testid={`breakdown-segment-${seg.key}`}
                  className={`${seg.colorClass} h-full transition-all duration-300`}
                  style={{ width: `${(seg.count / totalEvaluated) * 100}%` }}
                  title={`${seg.label}: ${pluralize(seg.count, "clause")}`}
                />
              ))}
            </div>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[10px] text-[var(--muted-foreground)]">
              {segments.map((seg) => (
                <span key={seg.key} className="inline-flex items-center gap-1.5">
                  <span className={`w-2 h-2 rounded-full ${seg.colorClass}`} />
                  <span>
                    {seg.label}: <strong className="text-[var(--foreground)]">{seg.count}</strong>
                  </span>
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

"use client";

import * as React from "react";
import { DocumentAnalysis } from "@/types/analysis";
import { FileDown, FileJson, FileText } from "lucide-react";
import { API_BASE_URL } from "@/lib/constants";
import { RiskChip } from "@/components/ui/risk-chip";
import { Button } from "@/components/ui/button";
import { pluralize } from "@/lib/utils";

interface AnalysisSummaryProps {
  analysis: DocumentAnalysis;
  documentId?: string;
  clauseCount?: number;
  className?: string;
}

export function AnalysisSummary({
  analysis,
  documentId,
  clauseCount,
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
      <div className={`p-6 rounded-[18px] border border-[var(--border)] bg-[var(--card)] flex flex-col md:flex-row items-start md:items-center justify-between gap-6 select-none ${className}`}>
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

  const distribution =
    typeof analysis.risk_distribution === "string"
      ? JSON.parse(analysis.risk_distribution)
      : analysis.risk_distribution || {};

  const standardCount =
    Number(distribution.standard || 0) + Number(distribution.low || 0) + Number(distribution.LOW || 0);
  const unusualCount =
    Number(distribution.slightly_unusual || 0);
  const oneSidedCount =
    Number(distribution.one_sided || 0) + Number(distribution.medium || 0) + Number(distribution.MEDIUM || 0);
  const highRiskCount =
    Number(distribution.high_risk || 0) + Number(distribution.high || 0) + Number(distribution.HIGH || 0);
  const unenforceableCount =
    Number(distribution.potentially_unenforceable || 0) + Number(distribution.critical || 0) + Number(distribution.CRITICAL || 0);

  let totalFromDistribution =
    standardCount + unusualCount + oneSidedCount + highRiskCount + unenforceableCount;

  if (totalFromDistribution === 0 && distribution && typeof distribution === "object") {
    if ("total_clauses" in distribution && Number(distribution.total_clauses) > 0) {
      totalFromDistribution = Number(distribution.total_clauses);
    } else {
      for (const val of Object.values(distribution)) {
        if (val && typeof val === "object" && "clause_count" in val) {
          totalFromDistribution += Number((val as { clause_count?: number }).clause_count || 0);
        }
      }
    }
  }

  const totalEvaluated = clauseCount || totalFromDistribution || 1;

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
    <div className={`space-y-4 select-none ${className}`}>
      {/* Main Overall Risk Card */}
      <div className="p-5 sm:p-6 rounded-[18px] border border-[var(--border)] bg-[var(--card)] space-y-3.5">
        {/* Top Alignment Bar: Badges on left, Download Options in-line on right */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-1 border-b border-[var(--border)]/30">
          <div className="flex items-center gap-2.5">
            <RiskChip category={overallCategory} size="sm" />
            <span className="text-xs text-[var(--muted-foreground)] font-medium">
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
            <span className="font-serif text-3xl font-bold text-[var(--foreground)] tabular-nums leading-none">
              {score}
            </span>
            <span className="text-[9px] font-semibold uppercase tracking-wider text-[var(--muted-foreground)] mt-1">
              Risk Score
            </span>
          </div>

          <p className="text-xs text-[var(--foreground)] leading-relaxed flex-1 text-justify [text-align:justify] [text-justify:inter-word]">
            {analysis.overall_summary ||
              "Contract clause risk analysis evaluated with sequential grounding against standard commercial precedents."}
          </p>
        </div>
      </div>
    </div>
  );
}

"use client";

import * as React from "react";
import { DocumentAnalysis } from "@/types/analysis";
import { FileJson, FileText, Scale } from "lucide-react";
import { API_BASE_URL } from "@/lib/constants";
import { RiskChip } from "@/components/ui/risk-chip";
import { Button } from "@/components/ui/button";

interface AnalysisSummaryProps {
  analysis: DocumentAnalysis;
  documentId?: string;
  className?: string;
}

export function AnalysisSummary({
  analysis,
  documentId,
  className = "",
}: AnalysisSummaryProps) {
  const score = analysis.overall_risk_score;

  let overallCategory = "standard";
  if (score >= 75) {
    overallCategory = "high_risk";
  } else if (score >= 50) {
    overallCategory = "one_sided";
  } else if (score >= 25) {
    overallCategory = "slightly_unusual";
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

  const totalEvaluated =
    standardCount + unusualCount + oneSidedCount + highRiskCount + unenforceableCount || 1;

  const handleDownload = (format: "json" | "markdown") => {
    const docId = documentId || analysis.document_id;
    if (!docId) return;
    const url = `${API_BASE_URL}/documents/${docId}/export/${format}`;
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;

    fetch(url, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then((res) => res.blob())
      .then((blob) => {
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = downloadUrl;
        a.download = `risk_analysis_export.${format === "json" ? "json" : "md"}`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(downloadUrl);
      })
      .catch((err) => console.error("Export download failed:", err));
  };

  return (
    <div className={`space-y-4 select-none ${className}`}>
      {/* Information, Not Legal Advice Banner */}
      <div
        role="note"
        aria-label="Legal Notice"
        className="p-3.5 rounded-[14px] bg-[var(--soft-surface)] border border-[var(--border)] text-[var(--foreground)] text-xs flex items-start gap-2.5"
      >
        <Scale className="w-4 h-4 text-[var(--accent)] shrink-0 mt-0.5" />
        <p className="leading-relaxed text-[var(--muted-foreground)]">
          <strong className="text-[var(--foreground)]">Information, not legal advice:</strong> Clause risk scores and plain English simplifications are AI-generated for exploratory analysis and do not constitute formal legal counsel.
        </p>
      </div>

      {/* Main Overall Risk Card */}
      <div className="p-5 sm:p-6 rounded-[18px] border border-[var(--border)] bg-[var(--card)] flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        {/* Score Pillar */}
        <div className="flex items-center gap-4">
          <div className="w-20 h-20 rounded-[14px] bg-[var(--soft-surface)] border border-[var(--border)] flex flex-col items-center justify-center shrink-0">
            <span className="font-serif text-3xl font-bold text-[var(--foreground)] tabular-nums leading-none">
              {score}
            </span>
            <span className="text-[9px] font-semibold uppercase tracking-wider text-[var(--muted-foreground)] mt-1">
              Risk Score
            </span>
          </div>

          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <RiskChip category={overallCategory} size="sm" />
              <span className="text-xs text-[var(--muted-foreground)] font-medium">
                {totalEvaluated} clauses evaluated
              </span>
            </div>
            <p className="text-xs text-[var(--foreground)] leading-relaxed max-w-xl">
              {analysis.overall_summary ||
                "Contract clause risk analysis evaluated with sequential grounding against standard commercial precedents."}
            </p>
          </div>
        </div>

        {/* Export Buttons */}
        <div className="flex items-center gap-2 self-stretch sm:self-auto shrink-0 justify-end">
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleDownload("markdown")}
            className="flex-1 sm:flex-initial"
          >
            <FileText className="w-3.5 h-3.5 mr-1" />
            <span>Export Markdown</span>
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleDownload("json")}
            className="flex-1 sm:flex-initial"
          >
            <FileJson className="w-3.5 h-3.5 mr-1" />
            <span>Export JSON</span>
          </Button>
        </div>
      </div>

      {/* Risk Distribution Breakdown Chips & Progress */}
      <div className="p-4 rounded-[14px] border border-[var(--border)] bg-[var(--card)] space-y-3">
        <div className="flex items-center justify-between flex-wrap gap-2 text-xs font-semibold text-[var(--foreground)]">
          <span>Clause Risk Breakdown</span>
          <div className="flex items-center gap-2 flex-wrap text-[11px]">
            <RiskChip category="standard" label={`Standard (${standardCount})`} size="sm" />
            {unusualCount > 0 && (
              <RiskChip category="slightly_unusual" label={`Unusual (${unusualCount})`} size="sm" />
            )}
            {oneSidedCount > 0 && (
              <RiskChip category="one_sided" label={`One-Sided (${oneSidedCount})`} size="sm" />
            )}
            {highRiskCount > 0 && (
              <RiskChip category="high_risk" label={`High Risk (${highRiskCount})`} size="sm" />
            )}
            {unenforceableCount > 0 && (
              <RiskChip
                category="potentially_unenforceable"
                label={`Review (${unenforceableCount})`}
                size="sm"
              />
            )}
          </div>
        </div>

        {/* Multi-segment Progress Bar */}
        <div className="h-2 w-full bg-[var(--soft-surface)] rounded-full overflow-hidden flex gap-0.5 border border-[var(--border)]">
          {standardCount > 0 && (
            <div
              style={{ width: `${(standardCount / totalEvaluated) * 100}%` }}
              className="bg-[#1F5C2E] dark:bg-[#7BE0A0] h-full transition-all"
              title={`Standard Clauses: ${standardCount}`}
            />
          )}
          {unusualCount > 0 && (
            <div
              style={{ width: `${(unusualCount / totalEvaluated) * 100}%` }}
              className="bg-[#6B4F00] dark:bg-[#F2D472] h-full transition-all"
              title={`Slightly Unusual: ${unusualCount}`}
            />
          )}
          {oneSidedCount > 0 && (
            <div
              style={{ width: `${(oneSidedCount / totalEvaluated) * 100}%` }}
              className="bg-[#8A3B00] dark:bg-[#FFB06B] h-full transition-all"
              title={`One-Sided: ${oneSidedCount}`}
            />
          )}
          {highRiskCount > 0 && (
            <div
              style={{ width: `${(highRiskCount / totalEvaluated) * 100}%` }}
              className="bg-[#8F1D1D] dark:bg-[#FF8F9B] h-full transition-all"
              title={`High Risk: ${highRiskCount}`}
            />
          )}
          {unenforceableCount > 0 && (
            <div
              style={{ width: `${(unenforceableCount / totalEvaluated) * 100}%` }}
              className="bg-[#5C0612] dark:bg-[#FF5C72] h-full transition-all"
              title={`Potentially Unenforceable: ${unenforceableCount}`}
            />
          )}
        </div>
      </div>
    </div>
  );
}

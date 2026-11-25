"use client";

import { useState } from "react";
import Link from "next/link";
import { useQueryClient } from "@tanstack/react-query";
import { useDocuments } from "@/hooks/use-documents";
import { apiClient } from "@/lib/api-client";
import { RiskChip } from "@/components/ui/risk-chip";
import { StatusBadge } from "@/components/documents/status-badge";
import { Button } from "@/components/ui/button";
import {
  ShieldAlert,
  Search,
  ArrowRight,
  FileText,
  AlertTriangle,
  UploadCloud,
  Zap,
} from "lucide-react";

export default function AnalysisIndexPage() {
  const queryClient = useQueryClient();
  const { data: docsData, isLoading, isError } = useDocuments(1, 50);
  const [searchTerm, setSearchTerm] = useState("");
  const [riskFilter, setRiskFilter] = useState<string>("all");

  const handlePrefetch = (docId: string) => {
    queryClient.prefetchQuery({
      queryKey: ['documents', docId],
      queryFn: async () => {
        const res = await apiClient.get(`/documents/${docId}`);
        return res.data.data;
      },
      staleTime: 5 * 60 * 1000,
    });
    queryClient.prefetchQuery({
      queryKey: ['analysis', docId, 'summary'],
      queryFn: async () => {
        const res = await apiClient.get(`/analysis/${docId}/summary`);
        return res.data.data;
      },
      staleTime: 5 * 60 * 1000,
    });
    queryClient.prefetchQuery({
      queryKey: ['analysis', docId, 'clauses'],
      queryFn: async () => {
        const res = await apiClient.get(`/analysis/${docId}/clauses`);
        return res.data.data;
      },
      staleTime: 5 * 60 * 1000,
    });
  };

  const documents = docsData?.items || [];

  // Filter documents that have been analyzed or are currently analyzing
  const analyzedDocs = documents.filter((d) => d.status === "completed" || d.overall_risk_score !== null);
  const totalAnalyzed = analyzedDocs.length;

  const highRiskCount = analyzedDocs.filter((d) => (d.overall_risk_score || 0) >= 50).length;
  const avgRiskScore =
    totalAnalyzed > 0
      ? Math.round(
          analyzedDocs.reduce((acc, d) => acc + (d.overall_risk_score || 0), 0) / totalAnalyzed
        )
      : 0;

  const filteredDocs = analyzedDocs.filter((doc) => {
    const matchesSearch =
      doc.original_filename.toLowerCase().includes(searchTerm.toLowerCase()) ||
      doc.document_type.toLowerCase().includes(searchTerm.toLowerCase());

    const score = doc.overall_risk_score || 0;
    let category = "standard";
    if (score >= 75) category = "high_risk";
    else if (score >= 50) category = "one_sided";
    else if (score >= 25) category = "slightly_unusual";

    const matchesRisk =
      riskFilter === "all" ||
      (riskFilter === "high" && (category === "high_risk" || category === "one_sided")) ||
      (riskFilter === "standard" && (category === "standard" || category === "slightly_unusual"));

    return matchesSearch && matchesRisk;
  });

  return (
    <div className="space-y-6 select-none max-w-6xl mx-auto pb-10">
      {/* Page Header */}
      <div>
        <h1 className="font-serif text-2xl sm:text-3xl font-semibold text-[var(--foreground)] tracking-tight">
          Clause Risk Analyses & Records
        </h1>
        <p className="text-xs sm:text-sm text-[var(--muted-foreground)] mt-1 max-w-2xl leading-relaxed">
          Comprehensive clause risk evaluations, extracted provisions, benchmark comparisons, and interactive viewer sessions for all analyzed contracts.
        </p>
      </div>

      {/* Summary Telemetry Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="p-5 rounded-[18px] bg-[var(--card)] border border-[var(--border)] space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-semibold tracking-wider text-[var(--muted-foreground)] uppercase">
              Analyzed Agreements
            </span>
            <div className="w-8 h-8 rounded-[8px] bg-[var(--soft-surface)] border border-[var(--border)] flex items-center justify-center text-[var(--accent)]">
              <FileText className="w-4 h-4" />
            </div>
          </div>
          <div className="font-serif text-3xl font-bold text-[var(--foreground)] tabular-nums">
            {totalAnalyzed}
          </div>
          <div className="text-[11px] text-[var(--muted-foreground)]">Completed RAG risk evaluations</div>
        </div>

        <div className="p-5 rounded-[18px] bg-[var(--card)] border border-[var(--border)] space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-semibold tracking-wider text-[var(--muted-foreground)] uppercase">
              Flagged Elevated Risk
            </span>
            <div className="w-8 h-8 rounded-[8px] bg-[var(--risk-high-bg)] border border-[var(--risk-high-border)] flex items-center justify-center text-[var(--risk-high-text)]">
              <AlertTriangle className="w-4 h-4" />
            </div>
          </div>
          <div className="font-serif text-3xl font-bold text-[var(--risk-high-text)] tabular-nums">
            {highRiskCount}
          </div>
          <div className="text-[11px] text-[var(--muted-foreground)]">Score ≥ 50 (One-Sided or High Risk)</div>
        </div>

        <div className="p-5 rounded-[18px] bg-[var(--card)] border border-[var(--border)] space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-semibold tracking-wider text-[var(--muted-foreground)] uppercase">
              Average Risk Score
            </span>
            <div className="w-8 h-8 rounded-[8px] bg-[var(--soft-surface)] border border-[var(--border)] flex items-center justify-center text-[var(--accent)]">
              <Zap className="w-4 h-4" />
            </div>
          </div>
          <div className="font-serif text-3xl font-bold text-[var(--foreground)] tabular-nums">
            {avgRiskScore} <span className="text-sm font-normal text-[var(--muted-foreground)]">/ 100</span>
          </div>
          <div className="text-[11px] text-[var(--muted-foreground)]">Mean across all analyzed clauses</div>
        </div>
      </div>

      {/* Control & Search Toolbar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 p-4 rounded-[14px] bg-[var(--card)] border border-[var(--border)]">
        <div className="flex flex-wrap items-center gap-2.5 flex-1">
          <div className="relative flex-1 sm:max-w-xs">
            <Search className="absolute left-3 top-2.5 w-3.5 h-3.5 text-[var(--muted-foreground)] pointer-events-none" />
            <input
              type="text"
              placeholder="Filter analyses by document name..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full h-9 pl-9 pr-3 rounded-[10px] bg-[var(--soft-surface)] border border-[var(--border)] text-xs text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
            />
          </div>

          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => setRiskFilter("all")}
              className={`px-3 py-1.5 rounded-[8px] text-xs font-medium transition-all ${
                riskFilter === "all"
                  ? "bg-[var(--accent)] text-[var(--accent-foreground)] font-semibold shadow-xs"
                  : "bg-[var(--soft-surface)] text-[var(--muted-foreground)] hover:text-[var(--foreground)] border border-[var(--border)]"
              }`}
            >
              All
            </button>
            <button
              type="button"
              onClick={() => setRiskFilter("high")}
              className={`px-3 py-1.5 rounded-[8px] text-xs font-medium transition-all ${
                riskFilter === "high"
                  ? "bg-[var(--risk-high-bg)] text-[var(--risk-high-text)] font-semibold border border-[var(--risk-high-border)] shadow-xs"
                  : "bg-[var(--soft-surface)] text-[var(--muted-foreground)] hover:text-[var(--foreground)] border border-[var(--border)]"
              }`}
            >
              Elevated Risk
            </button>
            <button
              type="button"
              onClick={() => setRiskFilter("standard")}
              className={`px-3 py-1.5 rounded-[8px] text-xs font-medium transition-all ${
                riskFilter === "standard"
                  ? "bg-[var(--risk-standard-bg)] text-[var(--risk-standard-text)] font-semibold border border-[var(--risk-standard-border)] shadow-xs"
                  : "bg-[var(--soft-surface)] text-[var(--muted-foreground)] hover:text-[var(--foreground)] border border-[var(--border)]"
              }`}
            >
              Standard
            </button>
          </div>
        </div>

        <Link href="/upload">
          <Button size="sm" className="w-full sm:w-auto">
            <UploadCloud className="w-3.5 h-3.5 mr-1" />
            <span>New Analysis</span>
          </Button>
        </Link>
      </div>

      {/* Analysis Records Grid */}
      <div className="space-y-4">
        {isLoading ? (
          <div className="p-12 text-center text-[var(--muted-foreground)] text-xs space-y-3 rounded-[18px] bg-[var(--card)] border border-[var(--border)]">
            <div className="w-7 h-7 rounded-full border-2 border-[var(--accent)] border-t-transparent animate-spin mx-auto" />
            <p>Loading analysis records...</p>
          </div>
        ) : isError ? (
          <div className="p-6 text-center text-[var(--risk-high-text)] text-xs bg-[var(--risk-high-bg)] border border-[var(--risk-high-border)] rounded-[18px] flex items-center justify-center gap-2">
            <AlertTriangle className="w-4 h-4" />
            <span>Failed to connect to analysis service. Please verify backend is running.</span>
          </div>
        ) : filteredDocs.length === 0 ? (
          <div className="p-12 text-center rounded-[18px] bg-[var(--card)] border border-[var(--border)] space-y-3">
            <div className="w-12 h-12 rounded-[14px] bg-[var(--soft-surface)] flex items-center justify-center mx-auto text-[var(--muted-foreground)]">
              <ShieldAlert className="w-6 h-6" />
            </div>
            <h3 className="font-serif text-base font-semibold text-[var(--foreground)]">
              {totalAnalyzed === 0 ? "No Contract Analyses Yet" : "No Analyses Matched Filter"}
            </h3>
            <p className="text-xs text-[var(--muted-foreground)] max-w-sm mx-auto leading-relaxed">
              {totalAnalyzed === 0
                ? "Upload a contract or Terms of Service PDF to run clause-level segmentation and RAG risk benchmarking."
                : `No analyses match your current search or risk filter.`}
            </p>
            {totalAnalyzed === 0 && (
              <Link href="/upload">
                <Button size="sm">
                  <UploadCloud className="w-3.5 h-3.5 mr-1" />
                  <span>Start First Analysis</span>
                </Button>
              </Link>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredDocs.map((doc) => {
              const riskScore = doc.overall_risk_score;
              let riskCategory = "standard";
              if (riskScore !== null && riskScore !== undefined) {
                if (riskScore >= 75) riskCategory = "high_risk";
                else if (riskScore >= 50) riskCategory = "one_sided";
                else if (riskScore >= 25) riskCategory = "slightly_unusual";
              }

              return (
                <div
                  key={doc.id}
                  className="p-5 rounded-[18px] bg-[var(--card)] border border-[var(--border)] space-y-4 flex flex-col justify-between shadow-none hover:border-[var(--accent)]/50 transition-colors"
                >
                  <div className="space-y-3">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
                        {doc.document_type === "non_legal"
                          ? "Non-Legal Document"
                          : doc.document_type.replace(/_/g, " ").toUpperCase()}
                      </span>
                      {riskScore !== null && riskScore !== undefined ? (
                        <RiskChip category={riskCategory} score={riskScore} size="sm" />
                      ) : doc.document_type === "non_legal" ? (
                        <span className="text-[11px] font-medium text-[var(--muted-foreground)]">Non-Legal</span>
                      ) : (
                        <StatusBadge status={doc.status} />
                      )}
                    </div>

                    <div>
                      <h3 className="font-serif text-base font-semibold text-[var(--foreground)] truncate">
                        {doc.original_filename}
                      </h3>
                      <p className="text-[11px] text-[var(--muted-foreground)] mt-0.5">
                        Uploaded on {new Date(doc.created_at).toLocaleDateString()}
                      </p>
                    </div>

                    {/* Risk Score Progress Bar */}
                    {doc.document_type !== "non_legal" && riskScore !== null && riskScore !== undefined ? (
                      <div className="space-y-1">
                        <div className="flex justify-between text-[10px] text-[var(--muted-foreground)]">
                          <span>Risk Severity</span>
                          <span className="font-semibold text-[var(--foreground)]">{riskScore || 0}/100</span>
                        </div>
                        <div className="h-1.5 w-full rounded-full bg-[var(--soft-surface)] overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all duration-300 ${
                              (riskScore || 0) >= 75
                                ? "bg-[var(--risk-high-text)]"
                                : (riskScore || 0) >= 50
                                ? "bg-[var(--risk-onesided-text)]"
                                : (riskScore || 0) >= 25
                                ? "bg-[var(--risk-unusual-text)]"
                                : "bg-[var(--risk-standard-text)]"
                            }`}
                            style={{ width: `${Math.min(100, riskScore || 0)}%` }}
                          />
                        </div>
                      </div>
                    ) : (
                      <p className="text-[11px] text-[var(--muted-foreground)] italic">
                        {doc.document_type === "non_legal"
                          ? "Risk scoring skipped (non-legal document)"
                          : "Analysis pending..."}
                      </p>
                    )}
                  </div>

                  {/* Open Viewer CTA */}
                  <div className="pt-3 border-t border-[var(--border)] flex items-center justify-between gap-2">
                    <span className="text-[11px] text-[var(--muted-foreground)]">
                      Synchronized PDF & Clause Panel
                    </span>
                    <Link
                      href={`/analysis/${doc.id}`}
                      onMouseEnter={() => handlePrefetch(doc.id)}
                      onFocus={() => handlePrefetch(doc.id)}
                    >
                      <Button size="sm" className="h-8 text-xs">
                        <span>Open Viewer</span>
                        <ArrowRight className="w-3.5 h-3.5 ml-1" />
                      </Button>
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

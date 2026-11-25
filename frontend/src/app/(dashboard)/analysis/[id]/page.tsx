"use client";

import { use, useState } from "react";
import Link from "next/link";
import { useDocument, useResumeDocument } from "@/hooks/use-documents";
import { useDocumentSummary, useClauseAnalyses } from "@/hooks/use-analysis";
import { StatusBadge } from "@/components/documents/status-badge";
import {
  ArrowLeft,
  Loader2,
  AlertCircle,
  Clock,
  FileText,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { AnalysisSummary } from "@/components/analysis/analysis-summary";
import { ClauseDetailPanel } from "@/components/analysis/clause-detail-panel";
import { DocumentViewer } from "@/components/pdf-viewer/viewer";
import { Skeleton } from "@/components/ui/skeleton";
import { pluralize } from "@/lib/utils";

export default function AnalysisPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [activeClauseId, setActiveClauseId] = useState<string | null>(null);

  const { data: document, isLoading: docLoading, isError: docError, refetch: refetchDoc } = useDocument(id);
  const resumeMutation = useResumeDocument();
  const isAnalyzing = document?.status === "analyzing";
  const isCompleted = document?.status === "completed";

  // Only fetch summary when document is completed to prevent 404 polling flicker while clauses are streaming
  const { data: summary, isLoading: summaryLoading } = useDocumentSummary(id, isCompleted, false);
  const { data: clauses, isLoading: clausesLoading } = useClauseAnalyses(id, !!id, isAnalyzing);

  // Initial loading state: clean centered loader while document metadata is retrieved
  if (docLoading && !document) {
    return (
      <div className="p-12 text-center rounded-[18px] border border-[var(--border)] bg-[var(--card)] flex flex-col items-center justify-center min-h-[400px] animate-in fade-in duration-150 max-w-xl mx-auto my-12">
        <div className="w-12 h-12 rounded-[14px] bg-[var(--soft-surface)] flex items-center justify-center mb-4 text-[var(--accent)]">
          <Loader2 className="w-6 h-6 animate-spin" />
        </div>
        <h2 className="font-serif text-base font-semibold text-[var(--foreground)] mb-1">
          Loading Document...
        </h2>
        <p className="text-xs text-[var(--muted-foreground)] max-w-sm leading-relaxed">
          Retrieving contract records and analysis status.
        </p>
      </div>
    );
  }

  // Error / Not Found state
  if (docError || !document) {
    return (
      <div className="p-8 sm:p-12 text-center max-w-md mx-auto my-12 bg-[var(--card)] border border-[var(--risk-high-border)] rounded-[18px] shadow-sm">
        <div className="w-12 h-12 rounded-[14px] bg-[var(--risk-high-bg)] flex items-center justify-center mx-auto mb-4 text-[var(--risk-high-text)]">
          <AlertCircle className="w-6 h-6" />
        </div>
        <h3 className="font-serif text-lg font-semibold text-[var(--foreground)] mb-1">
          Document Not Found
        </h3>
        <p className="text-xs text-[var(--muted-foreground)] mb-6 leading-relaxed">
          The requested document analysis could not be located. It may have been removed or you may have followed an expired link.
        </p>
        <Link
          href="/documents"
          className="inline-flex items-center justify-center px-4 py-2 text-xs font-medium text-[var(--accent-foreground)] rounded-[10px] bg-[var(--accent)] hover:opacity-90 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
        >
          Return to Documents
        </Link>
      </div>
    );
  }

  const isProcessing = ["uploaded", "extracting", "segmenting", "analyzing"].includes(
    document.status
  );

  const selectedClause = (clauses || []).find((c) => c.id === activeClauseId) || (clauses && clauses.length > 0 ? clauses[0] : null);

  const handleClauseSelect = (clauseId: string) => {
    setActiveClauseId(clauseId === activeClauseId ? null : clauseId);
  };

  return (
    <div className="flex-1 flex flex-col space-y-6 select-none">
      {/* Workspace Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[var(--border)] shrink-0">
        <div className="flex items-center gap-3.5">
          <Link
            href="/documents"
            className="p-2 rounded-[10px] bg-[var(--card)] border border-[var(--border)] hover:bg-[var(--soft-surface)] text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
            aria-label="Return to document list"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <h1 className="font-serif text-lg sm:text-xl font-semibold text-[var(--foreground)] tracking-tight flex items-center gap-2">
              <FileText className="w-4 h-4 text-[var(--accent)] shrink-0" />
              <span className="truncate max-w-md sm:max-w-xl">{document.original_filename}</span>
            </h1>
            <div className="flex items-center gap-2 mt-0.5 text-xs text-[var(--muted-foreground)]">
              <span>{document.document_type === "non_legal" ? "Non-Legal Document" : document.document_type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}</span>
              {document.jurisdiction && (
                <>
                  <span>•</span>
                  <span className="font-medium text-[var(--foreground)]">
                    {document.jurisdiction.toUpperCase() === "IN"
                      ? "India"
                      : document.jurisdiction.toUpperCase() === "US"
                      ? "United States"
                      : document.jurisdiction.toUpperCase() === "EU"
                      ? "European Union"
                      : document.jurisdiction.toUpperCase() === "UK"
                      ? "United Kingdom"
                      : document.jurisdiction}
                  </span>
                </>
              )}
              <span>•</span>
              <StatusBadge status={document.status} />
            </div>
          </div>
        </div>
      </div>

      {/* Non-Legal Document State */}
      {document.document_type === "non_legal" ? (
        <div className="space-y-6">
          {summaryLoading ? (
            <Skeleton className="w-full h-36" rounded="card" />
          ) : summary ? (
            <AnalysisSummary analysis={summary} documentId={id} />
          ) : null}
          <div className="p-8 text-center rounded-[18px] border border-[var(--border)] bg-[var(--card)] max-w-xl mx-auto space-y-4">
            <div className="w-12 h-12 rounded-[14px] bg-[var(--soft-surface)] flex items-center justify-center mx-auto text-[var(--muted-foreground)]">
              <FileText className="w-6 h-6" />
            </div>
            <div className="space-y-1">
              <h3 className="font-serif text-base font-semibold text-[var(--foreground)]">
                Contract Risk Scoring Skipped
              </h3>
              <p className="text-xs text-[var(--muted-foreground)] leading-relaxed">
                This document was classified as non-legal material (such as technical documentation or a setup guide). The system intentionally skips clause risk scoring to prevent invented legal claims.
              </p>
            </div>
            <Link href="/upload" className="inline-block">
              <Button size="sm" className="text-xs">
                <span>Upload a Legal Contract</span>
              </Button>
            </Link>
          </div>
        </div>
      ) : isProcessing && (!clauses || clauses.length === 0) ? (
        /* Early processing before first clauses stream in */
        <div className="p-12 text-center rounded-[18px] border border-[var(--border)] bg-[var(--card)] flex flex-col items-center justify-center min-h-[350px]">
          <div className="w-12 h-12 rounded-[14px] bg-[var(--soft-surface)] flex items-center justify-center mb-4 text-[var(--accent)]">
            <Loader2 className="w-6 h-6 animate-spin" />
          </div>
          <h2 className="font-serif text-base font-semibold text-[var(--foreground)] mb-1">
            Analyzing Contract Clauses...
          </h2>
          <p className="text-xs text-[var(--muted-foreground)] max-w-sm leading-relaxed">
            Extracting clauses, comparing against commercial benchmarks, and generating plain English simplifications. This view updates automatically.
          </p>
          <div className="mt-5">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => refetchDoc()}
              className="text-xs h-8 gap-1.5"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Check Status</span>
            </Button>
          </div>
        </div>
      ) : document.status === "waiting for quota" ? (
        <div className="p-12 text-center rounded-[18px] border border-[var(--risk-unusual-border)] bg-[var(--risk-unusual-bg)] flex flex-col items-center justify-center min-h-[350px]">
          <div className="w-12 h-12 rounded-[14px] bg-[var(--card)] flex items-center justify-center mb-4 text-[var(--risk-unusual-text)]">
            <Clock className="w-6 h-6 animate-pulse" />
          </div>
          <h2 className="font-serif text-base font-semibold text-[var(--risk-unusual-text)] mb-1">
            Daily Quota Limit Reached
          </h2>
          <p className="text-xs text-[var(--risk-unusual-text)] max-w-md leading-relaxed mb-6">
            The Google Gemini API daily quota for this tier is temporarily exhausted. All analyzed clauses and document state are safely saved in the database checkpoint.
          </p>
          <div className="flex flex-col sm:flex-row items-center gap-3">
            <Button
              type="button"
              variant="default"
              size="sm"
              disabled={resumeMutation.isPending}
              onClick={() => resumeMutation.mutate(id)}
              className="text-xs h-8 gap-1.5 bg-[var(--accent)] text-[var(--accent-foreground)] hover:opacity-90"
            >
              {resumeMutation.isPending ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Resuming Analysis...</span>
                </>
              ) : (
                <>
                  <RefreshCw className="w-3.5 h-3.5" />
                  <span>Resume Analysis Now</span>
                </>
              )}
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => refetchDoc()}
              className="text-xs h-8 gap-1.5"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Check Status</span>
            </Button>
          </div>
          <p className="text-[11px] text-[var(--muted-foreground)] mt-4">
            Daily quota resets at 00:00 UTC. Click &quot;Resume Analysis Now&quot; to process remaining clauses without re-analyzing completed ones.
          </p>
        </div>
      ) : document.status === "failed" ? (
        <div className="p-12 text-center rounded-[18px] border border-[var(--risk-high-border)] bg-[var(--card)] flex flex-col items-center justify-center min-h-[350px]">
          <div className="w-12 h-12 rounded-[14px] bg-[var(--risk-high-bg)] flex items-center justify-center mb-4 text-[var(--risk-high-text)]">
            <AlertCircle className="w-6 h-6" />
          </div>
          <h2 className="font-serif text-base font-semibold text-[var(--foreground)] mb-1">
            Analysis Could Not Be Completed
          </h2>
          <p className="text-xs text-[var(--muted-foreground)] max-w-md mb-6 leading-relaxed">
            The document could not be processed. This typically occurs with encrypted PDFs, scanned raster images without machine-readable text, or temporary API quota exhaustion.
          </p>
          <div className="flex items-center gap-3">
            <Button
              type="button"
              variant="default"
              size="sm"
              disabled={resumeMutation.isPending}
              onClick={() => resumeMutation.mutate(id)}
              className="text-xs h-8 gap-1.5 bg-[var(--accent)] text-[var(--accent-foreground)] hover:opacity-90"
            >
              {resumeMutation.isPending ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Retrying...</span>
                </>
              ) : (
                <>
                  <RefreshCw className="w-3.5 h-3.5" />
                  <span>Retry Analysis</span>
                </>
              )}
            </Button>
            <Link
              href="/upload"
              className="inline-flex items-center justify-center px-4 py-1.5 text-xs font-medium text-[var(--muted-foreground)] rounded-[10px] border border-[var(--border)] hover:bg-[var(--soft-surface)] transition-all"
            >
              Upload Another Document
            </Link>
          </div>
        </div>
      ) : (
        <div className="space-y-6 flex-1 flex flex-col">
          {/* Live In-Progress Streaming Banner */}
          {isProcessing && (
            <div className="p-3 px-4 rounded-[14px] border border-[var(--accent)]/30 bg-[var(--soft-surface)] flex items-center justify-between gap-3 text-xs">
              <div className="flex items-center gap-2.5 text-[var(--foreground)]">
                <Loader2 className="w-4 h-4 animate-spin text-[var(--accent)] shrink-0" />
                <span className="font-semibold">Analysis in progress:</span>
                <span className="text-[var(--muted-foreground)]">
                  {clauses && clauses.length > 0
                    ? `Live streaming active — ${pluralize(clauses.length, "clause")} analyzed so far.`
                    : "Processing document..."}
                </span>
              </div>
              <span className="text-[11px] font-mono text-[var(--muted-foreground)]">Auto-updating</span>
            </div>
          )}

          {/* Top Overall Risk Summary & Risk Count Chips */}
          {summary ? (
            <AnalysisSummary
              analysis={summary}
              documentId={id}
              clauseCount={clauses?.length}
            />
          ) : isCompleted && summaryLoading ? (
            <div className="p-6 rounded-[18px] border border-[var(--border)] bg-[var(--card)] flex items-center justify-between gap-6 min-h-[120px] animate-pulse">
              <div className="flex items-center gap-4">
                <div className="w-16 h-16 rounded-[14px] bg-[var(--soft-surface)] flex items-center justify-center shrink-0 text-[var(--accent)]">
                  <Loader2 className="w-6 h-6 animate-spin" />
                </div>
                <div className="space-y-1.5">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-[var(--soft-surface)] text-[var(--accent)] border border-[var(--border)]">
                      Synthesizing Brief
                    </span>
                  </div>
                  <h3 className="font-serif text-sm font-semibold text-[var(--foreground)]">
                    Generating Executive Risk Summary...
                  </h3>
                  <p className="text-xs text-[var(--muted-foreground)]">
                    Aggregating clause evaluations and comparing against commercial benchmarks.
                  </p>
                </div>
              </div>
            </div>
          ) : null}

          {/* Two-Column Workspace: Viewer (Left) + Detail Panel (Right) */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 flex-1 items-start min-h-[600px]">
            {/* Left Column: PDF Viewer with Clause List and Search */}
            <div className="lg:col-span-7 xl:col-span-7 h-[650px] lg:h-[750px]">
              {clausesLoading && !clauses ? (
                <Skeleton className="w-full h-full" rounded="card" />
              ) : (
                <DocumentViewer
                  document={document}
                  clauses={clauses || []}
                  activeClauseId={activeClauseId}
                  onClauseSelect={handleClauseSelect}
                  className="h-full"
                />
              )}
            </div>

            {/* Right Column: Clause Detail Panel (Desktop) */}
            <div className="hidden lg:block lg:col-span-5 xl:col-span-5 h-[650px] lg:h-[750px] sticky top-20">
              <ClauseDetailPanel
                clause={selectedClause}
                className="h-full"
              />
            </div>

            {/* Mobile Bottom Sheet (Narrow Screens) */}
            {activeClauseId && (
              <div
                className="lg:hidden fixed inset-x-0 bottom-0 z-50 p-4 bg-black/50 backdrop-blur-xs flex justify-center"
                role="dialog"
                aria-modal="true"
                aria-label="Clause Details Sheet"
              >
                <div className="w-full max-w-lg max-h-[80vh] bg-[var(--card)] rounded-t-[18px] border border-[var(--border)] shadow-2xl flex flex-col overflow-hidden animate-in slide-in-from-bottom duration-200">
                  <div className="w-12 h-1.5 bg-[var(--border)] rounded-full mx-auto my-2 shrink-0" />
                  <ClauseDetailPanel
                    clause={selectedClause}
                    onClose={() => setActiveClauseId(null)}
                    className="border-none rounded-none shadow-none flex-1"
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

"use client";

import { use, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  useDocument,
  useDeleteDocument,
  useResumeDocument,
  isActiveDocumentStatus,
} from "@/hooks/use-documents";
import {
  useAnalysisStatus,
  useAnalysisStream,
  useDocumentSummary,
  useClauseAnalyses,
} from "@/hooks/use-analysis";
import { StatusBadge } from "@/components/documents/status-badge";
import {
  ArrowLeft,
  Loader2,
  AlertCircle,
  Clock,
  FileText,
  RefreshCw,
  Trash2,
  Ban,
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
  const router = useRouter();
  const [activeClauseId, setActiveClauseId] = useState<string | null>(null);
  const [isStoppingDelete, setIsStoppingDelete] = useState(false);

  const {
    data: document,
    isLoading: docLoading,
    isError: docError,
    refetch: refetchDoc,
    isFetching: docFetching,
  } = useDocument(id);

  const resumeMutation = useResumeDocument();
  const deleteMutation = useDeleteDocument();

  const isProcessing = isActiveDocumentStatus(document?.status);
  const isCompleted = document?.status === "completed";

  const { data: statusData, refetch: refetchStatus } = useAnalysisStatus(
    id,
    !!id &&
      (isProcessing ||
        document?.status === "waiting for quota" ||
        document?.status === "cancelling" ||
        document?.status === "failed" ||
        document?.status === "interrupted")
  );
  const { isProvisional } = useAnalysisStream(
    id,
    !!id && (isProcessing || document?.status === "cancelling") && !isStoppingDelete
  );

  const currentStage =
    statusData?.stage ||
    (document?.status ? String(document.status).toLowerCase() : "");
  const isCompletedOrScoring =
    isCompleted || isProvisional || currentStage === "scoring" || currentStage === "summarizing";

  const { data: summary, isLoading: summaryLoading } = useDocumentSummary(
    id,
    isCompletedOrScoring,
    isProvisional || currentStage === "scoring" || currentStage === "summarizing"
  );

  const {
    data: clauses,
    isLoading: clausesLoading,
    refetch: refetchClauses,
    isFetching: clausesFetching,
  } = useClauseAnalyses(id, !!id, isProcessing);

  const handleDelete = async () => {
    setIsStoppingDelete(true);
    try {
      await deleteMutation.mutateAsync(id);
      router.push("/documents");
    } catch {
      setIsStoppingDelete(false);
    }
  };

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

  const rawStatus = isStoppingDelete
    ? "cancelling"
    : String(statusData?.status || document.status || "").toLowerCase();
  const jobStatus = isStoppingDelete
    ? "cancelling"
    : String(statusData?.job_status || "").toLowerCase();

  const isQueued =
    !isStoppingDelete &&
    (rawStatus === "queued" || rawStatus === "uploaded" || jobStatus === "queued");
  const isWaitingForQuota =
    rawStatus === "waiting for quota" ||
    rawStatus === "waiting_for_quota" ||
    jobStatus === "waiting_for_quota";
  const isCancelling =
    isStoppingDelete || rawStatus === "cancelling" || jobStatus === "cancelling";
  const isCancelled = rawStatus === "cancelled" || jobStatus === "cancelled";
  const isFailed =
    rawStatus === "failed" ||
    rawStatus === "interrupted" ||
    jobStatus === "failed" ||
    jobStatus === "interrupted";

  const totalClauses = statusData?.total_clauses || clauses?.length || 0;
  const analyzedClauses = statusData?.analyzed_clauses ?? clauses?.length ?? 0;

  const selectedClause =
    (clauses || []).find((c) => c.id === activeClauseId) ||
    (clauses && clauses.length > 0 ? clauses[0] : null);

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
            <div className="flex flex-wrap items-center gap-2 mt-0.5 text-xs text-[var(--muted-foreground)]">
              <span>
                {document.document_type === "non_legal"
                  ? "Non-Legal Document"
                  : document.document_type
                      .replace(/_/g, " ")
                      .replace(/\b\w/g, (c) => c.toUpperCase())}
              </span>
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
              <StatusBadge
                status={isCancelling ? "cancelling" : rawStatus}
                stage={statusData?.stage}
                analyzedClauses={analyzedClauses}
                totalClauses={totalClauses}
              />
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <Button
            type="button"
            variant="outline"
            size="sm"
            data-testid="delete-document-button"
            disabled={isCancelling || deleteMutation.isPending}
            onClick={handleDelete}
            className="h-8 text-xs gap-1.5 border-[var(--risk-high-border)] text-[var(--risk-high-text)] hover:bg-[var(--risk-high-bg)]"
          >
            {isCancelling || deleteMutation.isPending ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Stopping analysis...</span>
              </>
            ) : (
              <>
                <Trash2 className="w-3.5 h-3.5" />
                <span>Delete</span>
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Cancelling Banner */}
      {isCancelling && (
        <div
          data-testid="stopping-analysis-banner"
          className="p-4 rounded-[14px] border border-amber-500/30 bg-amber-500/10 flex items-center gap-3 text-xs text-amber-300"
        >
          <Loader2 className="w-4 h-4 animate-spin shrink-0" />
          <span className="font-semibold">Stopping analysis...</span>
          <span>Waiting for worker confirmation before removing document records.</span>
        </div>
      )}

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
      ) : isCancelled && (!clauses || clauses.length === 0) ? (
        <div className="p-12 text-center rounded-[18px] border border-[var(--border)] bg-[var(--card)] flex flex-col items-center justify-center min-h-[320px]">
          <div className="w-12 h-12 rounded-[14px] bg-[var(--soft-surface)] flex items-center justify-center mb-4 text-[var(--muted-foreground)]">
            <Ban className="w-6 h-6" />
          </div>
          <h2 className="font-serif text-base font-semibold text-[var(--foreground)] mb-1">
            Analysis Cancelled
          </h2>
          <p className="text-xs text-[var(--muted-foreground)] max-w-md mb-6 leading-relaxed">
            Processing was stopped before completion. You can start a fresh analysis or upload another contract.
          </p>
          <Button
            type="button"
            variant="default"
            size="sm"
            disabled={resumeMutation.isPending}
            onClick={() => resumeMutation.mutate(id)}
            className="text-xs h-8 gap-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${resumeMutation.isPending ? "animate-spin" : ""}`} />
            <span>{resumeMutation.isPending ? "Restarting..." : "Retry Analysis"}</span>
          </Button>
        </div>
      ) : isFailed ? (
        <div className="p-12 text-center rounded-[18px] border border-[var(--risk-high-border)] bg-[var(--card)] flex flex-col items-center justify-center min-h-[350px]">
          <div className="w-12 h-12 rounded-[14px] bg-[var(--risk-high-bg)] flex items-center justify-center mb-4 text-[var(--risk-high-text)]">
            <AlertCircle className="w-6 h-6" />
          </div>
          <h2 className="font-serif text-base font-semibold text-[var(--foreground)] mb-1">
            {rawStatus === "interrupted"
              ? "Analysis Interrupted"
              : "Analysis Could Not Be Completed"}
          </h2>
          <p className="text-xs text-[var(--muted-foreground)] max-w-md mb-6 leading-relaxed">
            {statusData?.message ||
              "The document could not be finished cleanly. You can retry analysis to resume from the latest saved checkpoint."}
          </p>
          <div className="flex items-center gap-3">
            <Button
              type="button"
              variant="default"
              size="sm"
              data-testid="retry-analysis-button"
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
          {/* Waiting for Quota Banner (always shown cleanly without fake countdown) */}
          {isWaitingForQuota && (
            <div
              data-testid="quota-pause-banner"
              className="p-5 rounded-[16px] border border-[var(--risk-unusual-border)] bg-[var(--risk-unusual-bg)] flex flex-col md:flex-row md:items-center justify-between gap-4"
            >
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-[12px] bg-[var(--card)] flex items-center justify-center text-[var(--risk-unusual-text)] shrink-0">
                  <Clock className="w-5 h-5" />
                </div>
                <div className="space-y-1">
                  <h2 className="font-serif text-sm font-semibold text-[var(--risk-unusual-text)]">
                    Paused: Daily Quota Limit Reached
                  </h2>
                  <p className="text-xs text-[var(--risk-unusual-text)] leading-relaxed max-w-2xl">
                    Analysis resumes automatically after the daily quota reset. Completed clauses ({analyzedClauses} of {totalClauses || analyzedClauses} clauses) remain safely saved.
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <Button
                  type="button"
                  variant="default"
                  size="sm"
                  data-testid="resume-analysis-button"
                  disabled={resumeMutation.isPending}
                  onClick={() => resumeMutation.mutate(id)}
                  className="text-xs h-8 gap-1.5 bg-[var(--accent)] text-[var(--accent-foreground)] hover:opacity-90"
                >
                  <RefreshCw
                    className={`w-3.5 h-3.5 ${resumeMutation.isPending ? "animate-spin" : ""}`}
                  />
                  <span>
                    {resumeMutation.isPending ? "Resuming..." : "Resume Analysis Now"}
                  </span>
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={docFetching}
                  onClick={() => {
                    void refetchDoc();
                    void refetchStatus();
                  }}
                  className="text-xs h-8 gap-1.5"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${docFetching ? "animate-spin" : ""}`} />
                  <span>Check Status</span>
                </Button>
              </div>
            </div>
          )}

          {/* Early Queued / Pre-Clause Processing Card */}
          {isProcessing && !isWaitingForQuota && !isCancelling && (!clauses || clauses.length === 0) ? (
            <div
              data-testid="job-progress-card"
              className="p-12 text-center rounded-[18px] border border-[var(--border)] bg-[var(--card)] flex flex-col items-center justify-center min-h-[300px]"
            >
              <div className="w-12 h-12 rounded-[14px] bg-[var(--soft-surface)] flex items-center justify-center mb-4 text-[var(--accent)]">
                {isQueued ? (
                  <Clock className="w-6 h-6" />
                ) : (
                  <Loader2 className="w-6 h-6 animate-spin" />
                )}
              </div>
              <h2 className="font-serif text-base font-semibold text-[var(--foreground)] mb-1">
                {isQueued
                  ? "Queued for Analysis"
                  : `Running: ${(statusData?.stage || rawStatus || "processing").replace(/_/g, " ")}`}
              </h2>
              <p className="text-xs text-[var(--muted-foreground)] max-w-sm leading-relaxed">
                {totalClauses > 0
                  ? `${analyzedClauses} of ${pluralize(totalClauses, "clause")} analyzed.`
                  : statusData?.current_step ||
                    "Extracting clauses, comparing against commercial benchmarks, and generating plain English simplifications."}
              </p>
              <div className="mt-5">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={docFetching || clausesFetching}
                  onClick={() => {
                    void refetchDoc();
                    void refetchStatus();
                    void refetchClauses();
                  }}
                  className="text-xs h-8 gap-1.5"
                >
                  <RefreshCw
                    className={`w-3.5 h-3.5 ${docFetching || clausesFetching ? "animate-spin" : ""}`}
                  />
                  <span>{docFetching || clausesFetching ? "Checking..." : "Check Status"}</span>
                </Button>
              </div>
            </div>
          ) : null}

          {/* Live In-Progress Streaming Banner once first clauses arrive */}
          {isProcessing && !isWaitingForQuota && !isCancelling && clauses && clauses.length > 0 && (
            <div
              data-testid="streaming-progress-banner"
              className="p-3 px-4 rounded-[14px] border border-[var(--accent)]/30 bg-[var(--soft-surface)] flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
            >
              <div className="flex items-center gap-2.5 text-[var(--foreground)]">
                <Loader2 className="w-4 h-4 animate-spin text-[var(--accent)] shrink-0" />
                <span className="font-semibold">
                  Stage: {(statusData?.stage || rawStatus || "analyzing").replace(/_/g, " ")}
                </span>
                <span className="text-[var(--muted-foreground)]" data-testid="clause-progress-counter">
                  {totalClauses > 0
                    ? `${analyzedClauses || clauses.length} of ${totalClauses} clauses analyzed`
                    : `${pluralize(clauses.length, "clause")} analyzed so far`}
                </span>
              </div>
              <div className="flex items-center gap-2.5 self-end sm:self-auto shrink-0">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={async () => {
                    await Promise.all([refetchDoc(), refetchStatus(), refetchClauses()]);
                  }}
                  disabled={docFetching || clausesFetching}
                  className="h-7 text-xs px-2.5 gap-1.5 bg-[var(--card)] hover:bg-[var(--soft-surface)] border-[var(--border)] transition-all"
                >
                  <RefreshCw
                    className={`w-3 h-3 ${docFetching || clausesFetching ? "animate-spin" : ""}`}
                  />
                  <span>{docFetching || clausesFetching ? "Checking..." : "Check Status"}</span>
                </Button>
                <span className="text-[11px] font-mono text-[var(--muted-foreground)] hidden md:inline">
                  Live SSE
                </span>
              </div>
            </div>
          )}

          {/* Top Overall Risk Summary & Risk Count Chips (supports provisional score before summary completes) */}
          {summary ? (
            <AnalysisSummary
              analysis={summary}
              documentId={id}
              clauses={clauses}
              clauseCount={clauses?.length || totalClauses}
              isProvisional={!isCompleted || isProvisional}
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
          {((clauses && clauses.length > 0) || !isProcessing) && !isWaitingForQuota && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 flex-1 items-start min-h-[600px]">
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

              <div className="hidden lg:block lg:col-span-5 xl:col-span-5 h-[650px] lg:h-[750px] sticky top-20">
                <ClauseDetailPanel clause={selectedClause} className="h-full" />
              </div>

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
          )}

          {/* Show streamed partial clauses cleanly underneath quota-pause banner */}
          {isWaitingForQuota && clauses && clauses.length > 0 && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 flex-1 items-start min-h-[500px]">
              <div className="lg:col-span-7 xl:col-span-7 h-[550px]">
                <DocumentViewer
                  document={document}
                  clauses={clauses}
                  activeClauseId={activeClauseId}
                  onClauseSelect={handleClauseSelect}
                  className="h-full"
                />
              </div>
              <div className="hidden lg:block lg:col-span-5 xl:col-span-5 h-[550px]">
                <ClauseDetailPanel clause={selectedClause} className="h-full" />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

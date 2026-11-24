"use client";

import { use, useState } from "react";
import Link from "next/link";
import { useDocument } from "@/hooks/use-documents";
import { useDocumentSummary, useClauseAnalyses } from "@/hooks/use-analysis";
import { StatusBadge } from "@/components/documents/status-badge";
import {
  ArrowLeft,
  Loader2,
  AlertCircle,
  Clock,
  FileText,
} from "lucide-react";
import { AnalysisSummary } from "@/components/analysis/analysis-summary";
import { ClauseDetailPanel } from "@/components/analysis/clause-detail-panel";
import { DocumentViewer } from "@/components/pdf-viewer/viewer";
import { Skeleton } from "@/components/ui/skeleton";

export default function AnalysisPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [activeClauseId, setActiveClauseId] = useState<string | null>(null);

  const { data: document, isLoading: docLoading, isError: docError } = useDocument(id);
  const isReady = !!document && document.status === "completed";
  const { data: summary, isLoading: summaryLoading } = useDocumentSummary(id, isReady);
  const { data: clauses, isLoading: clausesLoading } = useClauseAnalyses(id, isReady);

  // Loading skeleton state
  if (docLoading) {
    return (
      <div className="space-y-6 animate-in fade-in duration-150">
        <div className="flex items-center gap-4">
          <Skeleton className="w-9 h-9" />
          <div className="space-y-2">
            <Skeleton className="w-48 h-6" />
            <Skeleton className="w-24 h-4" />
          </div>
        </div>
        <Skeleton className="w-full h-36" rounded="card" />
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-[500px]">
          <Skeleton className="lg:col-span-7 h-[550px]" rounded="card" />
          <Skeleton className="lg:col-span-5 h-[550px]" rounded="card" />
        </div>
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
              <span className="capitalize">{document.document_type.replace(/_/g, " ")}</span>
              <span>•</span>
              <StatusBadge status={document.status} />
            </div>
          </div>
        </div>
      </div>

      {/* Processing / In-Progress State */}
      {isProcessing ? (
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
        </div>
      ) : document.status === "waiting for quota" ? (
        <div className="p-12 text-center rounded-[18px] border border-[var(--risk-unusual-border)] bg-[var(--risk-unusual-bg)] flex flex-col items-center justify-center min-h-[350px]">
          <div className="w-12 h-12 rounded-[14px] bg-[var(--card)] flex items-center justify-center mb-4 text-[var(--risk-unusual-text)]">
            <Clock className="w-6 h-6 animate-pulse" />
          </div>
          <h2 className="font-serif text-base font-semibold text-[var(--risk-unusual-text)] mb-1">
            Daily Quota Limit Reached
          </h2>
          <p className="text-xs text-[var(--risk-unusual-text)] max-w-md leading-relaxed">
            The Google Gemini API quota for this tier is temporarily exhausted. The document state is safely preserved and will automatically resume.
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
            The document could not be processed. This typically occurs with encrypted PDFs, scanned raster images without machine-readable text, or corrupt files.
          </p>
          <Link
            href="/upload"
            className="inline-flex items-center justify-center px-4 py-2 text-xs font-medium text-[var(--accent-foreground)] rounded-[10px] bg-[var(--accent)] hover:opacity-90 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          >
            Upload Another Document
          </Link>
        </div>
      ) : (
        <div className="space-y-6 flex-1 flex flex-col">
          {/* Top Overall Risk Summary & Risk Count Chips */}
          {summaryLoading ? (
            <Skeleton className="w-full h-36" rounded="card" />
          ) : summary ? (
            <AnalysisSummary analysis={summary} documentId={id} />
          ) : null}

          {/* Two-Column Workspace: Viewer (Left) + Detail Panel (Right) */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 flex-1 items-start min-h-[600px]">
            {/* Left Column: PDF Viewer with Clause List and Search */}
            <div className="lg:col-span-7 xl:col-span-7 h-[650px] lg:h-[750px]">
              {clausesLoading ? (
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

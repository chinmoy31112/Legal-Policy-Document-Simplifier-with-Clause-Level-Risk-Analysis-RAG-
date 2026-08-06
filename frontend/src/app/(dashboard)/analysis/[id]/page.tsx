"use client";

import { use, useState } from "react";
import Link from "next/link";
import { useDocument } from "@/hooks/use-documents";
import { useDocumentSummary, useClauseAnalyses } from "@/hooks/use-analysis";
import { StatusBadge } from "@/components/documents/status-badge";

import { ArrowLeft, Loader2, AlertCircle, ShieldCheck, Sparkles, FileText } from "lucide-react";
import { AnalysisSummary } from "@/components/analysis/analysis-summary";
import { ClauseCard } from "@/components/analysis/clause-card";
import { DocumentViewer } from "@/components/pdf-viewer/viewer";

export default function AnalysisPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [activeClauseId, setActiveClauseId] = useState<string | null>(null);

  const { data: document, isLoading: docLoading, isError: docError } = useDocument(id);

  const isReady = !!document && document.status === "completed";
  const { data: summary, isLoading: summaryLoading } = useDocumentSummary(id, isReady);
  const { data: clauses, isLoading: clausesLoading } = useClauseAnalyses(id, isReady);

  if (docLoading) {
    return (
      <div className="flex h-full items-center justify-center space-y-3 flex-col">
        <div className="w-10 h-10 rounded-full border-2 border-emerald-400 border-t-transparent animate-spin" />
        <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">Loading Executive Analysis Workspace...</p>
      </div>
    );
  }

  if (docError || !document) {
    return (
      <div className="p-12 text-center text-red-400 max-w-md mx-auto my-12 bg-slate-900 border border-red-500/30 rounded-3xl shadow-2xl">
        <AlertCircle className="w-10 h-10 mx-auto mb-4 text-red-400" />
        <h3 className="text-lg font-bold text-slate-100 mb-1">Document Record Not Found</h3>
        <p className="text-xs text-slate-400 mb-6">
          The requested document analysis could not be located in the active database.
        </p>
        <Link
          href="/documents"
          className="px-6 py-2.5 text-xs font-bold uppercase tracking-wider text-slate-950 rounded-xl bg-emerald-400 hover:bg-emerald-300 transition-all inline-block shadow-md shadow-emerald-500/20"
        >
          Return to Document Repository
        </Link>
      </div>
    );
  }

  const isProcessing = ["uploaded", "extracting", "segmenting", "analyzing"].includes(
    document.status
  );

  const handleClauseSelect = (clauseId: string) => {
    setActiveClauseId(clauseId === activeClauseId ? null : clauseId);

    if (clauseId !== activeClauseId) {
      const element = window.document.getElementById(`card-${clauseId}`);
      if (element) {
        element.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    }
  };

  return (
    <div className="h-full flex flex-col select-none">
      {/* Workspace Header */}
      <div className="flex items-center justify-between mb-6 shrink-0 border-b border-slate-800/80 pb-4">
        <div className="flex items-center space-x-4">
          <Link
            href="/documents"
            className="p-2.5 bg-slate-900 border border-slate-800 hover:bg-slate-800 rounded-xl transition-all text-slate-300 hover:text-white"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <h1 className="text-xl lg:text-2xl font-extrabold font-heading text-slate-100 tracking-tight flex items-center gap-2">
              <FileText className="w-5 h-5 text-emerald-400" />
              {document.original_filename}
            </h1>
            <div className="flex items-center space-x-3 mt-1 text-xs">
              <span className="text-slate-400 capitalize font-medium">
                Category: {document.document_type.replace("_", " ")}
              </span>
              <span className="text-slate-700">•</span>
              <StatusBadge status={document.status} />
            </div>
          </div>
        </div>
      </div>

      {isProcessing ? (
        <div className="flex-1 flex flex-col items-center justify-center border border-slate-800 rounded-3xl bg-slate-900/90 shadow-2xl p-12 text-center relative overflow-hidden">
          <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center mb-6 text-emerald-400 shadow-lg shadow-emerald-500/10">
            <Loader2 className="w-8 h-8 animate-spin" />
          </div>
          <h2 className="text-xl font-bold font-heading text-slate-100 mb-2">
            AI Clause Extraction & RAG Benchmarking in Progress
          </h2>
          <p className="text-xs text-slate-400 max-w-md leading-relaxed">
            Our pipeline is extracting clause text, retrieving reference standards, and generating structured Gemini 3.5 risk models. Results will load automatically.
          </p>
        </div>
      ) : document.status === "failed" ? (
        <div className="flex-1 flex items-center justify-center border border-red-500/30 rounded-3xl bg-red-950/10 p-12 text-center">
          <div className="max-w-md">
            <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
            <h2 className="text-xl font-bold font-heading text-slate-100 mb-2">Analysis Task Encountered an Error</h2>
            <p className="text-xs text-slate-400 mb-6 leading-relaxed">
              There was an issue analyzing this document. This usually happens if the PDF is password-protected or unreadable text format.
            </p>
            <Link
              href="/upload"
              className="px-6 py-2.5 text-xs font-bold uppercase tracking-wider text-slate-950 rounded-xl bg-emerald-400 hover:bg-emerald-300 transition-all inline-block shadow-md"
            >
              Re-upload Document
            </Link>
          </div>
        </div>
      ) : (
        <div className="flex-1 flex overflow-hidden border border-slate-800 rounded-3xl shadow-2xl bg-slate-900/90">
          {/* Left Panel: Executive Summary & Clause Breakdown Cards */}
          <div className="w-1/2 flex flex-col border-r border-slate-800 bg-slate-950/60 overflow-hidden">
            <div className="flex-1 overflow-y-auto p-6 space-y-8">
              {summaryLoading ? (
                <div className="space-y-4 animate-pulse">
                  <div className="h-36 bg-slate-900 rounded-2xl border border-slate-800 w-full" />
                </div>
              ) : summary ? (
                <div>
                  <AnalysisSummary analysis={summary} />
                </div>
              ) : null}

              <div>
                <div className="flex items-center justify-between mb-4 border-b border-slate-800 pb-3">
                  <h3 className="font-bold text-base font-heading text-slate-100 flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-emerald-400" /> Clause Risk Breakdown
                  </h3>
                  <span className="text-[11px] font-semibold text-slate-400 bg-slate-900 px-3 py-1 rounded-full border border-slate-800">
                    {clauses?.length || 0} Clauses Evaluated
                  </span>
                </div>

                {clausesLoading ? (
                  <div className="space-y-4 animate-pulse">
                    {[1, 2, 3].map((i) => (
                      <div key={i} className="h-28 bg-slate-900 rounded-2xl border border-slate-800 w-full" />
                    ))}
                  </div>
                ) : clauses && clauses.length > 0 ? (
                  <div className="space-y-4">
                    {clauses.map((clauseAnalysis) => (
                      <div key={clauseAnalysis.id} id={`card-${clauseAnalysis.id}`}>
                        <ClauseCard
                          clause={clauseAnalysis}
                          isSelected={activeClauseId === clauseAnalysis.id}
                          onClick={() => handleClauseSelect(clauseAnalysis.id)}
                        />
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-400 py-8 text-center">No clauses found for this document.</p>
                )}
              </div>
            </div>
          </div>

          {/* Right Panel: Interactive Document Viewer */}
          <div className="w-1/2 flex flex-col bg-slate-950/90 relative">
            {!clausesLoading && clauses && (
              <DocumentViewer
                document={document}
                clauses={clauses}
                activeClauseId={activeClauseId}
                onClauseSelect={handleClauseSelect}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}

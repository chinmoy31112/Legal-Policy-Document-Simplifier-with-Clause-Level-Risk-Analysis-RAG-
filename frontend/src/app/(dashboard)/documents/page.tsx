"use client";

import Link from "next/link";
import { useState, useTransition, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { useDocuments, useDeleteDocument } from "@/hooks/use-documents";
import { StatusBadge } from "@/components/documents/status-badge";
import {
  FileText,
  Trash2,
  ArrowRight,
  UploadCloud,
  Search,
  Filter,
<<<<<<< HEAD
  AlertTriangle,
  Download,
  BookOpen,
  History,
=======
  Clock,
  AlertTriangle
>>>>>>> b678432af63f3a4eb3d5c8ec4f5040c014cfed60
} from "lucide-react";
import { API_BASE_URL } from "@/lib/constants";
import { Button } from "@/components/ui/button";
import { RiskChip } from "@/components/ui/risk-chip";

<<<<<<< HEAD
function DocumentsContent() {
  const searchParams = useSearchParams();
  const initialTab = searchParams.get("tab") === "kb" ? "kb" : "history";
  const [activeTab, setActiveTab] = useState<"history" | "kb">(initialTab);
  const [searchTerm, setSearchTerm] = useState("");
  const [, startTransition] = useTransition();

=======
export default function DocumentsPage() {
  const [searchTerm, setSearchTerm] = useState("");
>>>>>>> b678432af63f3a4eb3d5c8ec4f5040c014cfed60
  const { data, isLoading, isError } = useDocuments(1, 50);
  const deleteMutation = useDeleteDocument();

  const documents = data?.items || [];

  const filteredDocs = documents.filter((doc) =>
    doc.original_filename.toLowerCase().includes(searchTerm.toLowerCase()) ||
    doc.document_type.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleExport = (docId: string, format: "json" | "markdown") => {
    const url = `${API_BASE_URL}/documents/${docId}/export/${format}`;
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;

    fetch(url, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then((res) => res.blob())
      .then((blob) => {
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = window.document.createElement("a");
        a.href = downloadUrl;
        a.download = `contract_analysis.${format === "json" ? "json" : "md"}`;
        window.document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(downloadUrl);
      })
      .catch((err) => console.error("Export download failed:", err));
  };

  return (
    <div className="space-y-6 select-none max-w-6xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="font-serif text-2xl font-semibold text-[var(--foreground)] tracking-tight">
            {activeTab === "kb" ? "Knowledge Base & Benchmarks" : "Document Repository"}
          </h1>
          <p className="text-xs text-[var(--muted-foreground)] mt-1">
            {activeTab === "kb"
              ? "Reference commercial clauses and standard baseline precedents for RAG retrieval"
              : "Complete history of uploaded agreements, audited clauses, and risk metrics"}
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center rounded-[10px] bg-[var(--soft-surface)] p-1 border border-[var(--border)] shrink-0">
          <button
            type="button"
            onClick={() => startTransition(() => setActiveTab("history"))}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[8px] text-xs font-medium transition-all ${
              activeTab === "history"
                ? "bg-[var(--card)] text-[var(--foreground)] font-semibold shadow-xs border border-[var(--border)]"
                : "text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
            }`}
          >
            <History className="w-3.5 h-3.5" />
            <span>Document History</span>
          </button>
          <button
            type="button"
            onClick={() => startTransition(() => setActiveTab("kb"))}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[8px] text-xs font-medium transition-all ${
              activeTab === "kb"
                ? "bg-[var(--card)] text-[var(--foreground)] font-semibold shadow-xs border border-[var(--border)]"
                : "text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
            }`}
          >
            <BookOpen className="w-3.5 h-3.5" />
            <span>Knowledge Base</span>
          </button>
        </div>
      </div>

      {/* Control Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 rounded-[14px] bg-[var(--card)] border border-[var(--border)]">
        <div className="flex flex-wrap items-center gap-2.5 flex-1">
          <div className="relative flex-1 sm:max-w-xs">
            <Search className="absolute left-3 top-2.5 w-3.5 h-3.5 text-[var(--muted-foreground)] pointer-events-none" />
            <input
              type="text"
              placeholder="Search contracts by name or type..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full h-9 pl-9 pr-3 rounded-[10px] bg-[var(--soft-surface)] border border-[var(--border)] text-xs text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
              aria-label="Search contracts"
            />
          </div>

          <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-[8px] bg-[var(--soft-surface)] border border-[var(--border)] text-xs font-medium text-[var(--muted-foreground)]">
            <Filter className="w-3 h-3 text-[var(--accent)]" />
            <span>{filteredDocs.length} Documents</span>
          </div>
        </div>

        <Link href="/upload">
          <Button size="sm" className="w-full sm:w-auto">
            <UploadCloud className="w-3.5 h-3.5 mr-1" />
            <span>Upload Contract</span>
          </Button>
        </Link>
      </div>

      {/* Documents Table */}
      <div className="rounded-[18px] bg-[var(--card)] border border-[var(--border)] overflow-hidden shadow-none">
        {isLoading ? (
          <div className="p-12 text-center text-[var(--muted-foreground)] text-xs space-y-3">
            <div className="w-7 h-7 rounded-full border-2 border-[var(--accent)] border-t-transparent animate-spin mx-auto" />
            <p>Loading document repository...</p>
          </div>
        ) : isError ? (
          <div className="p-8 text-center text-[var(--risk-high-text)] text-xs bg-[var(--risk-high-bg)] border border-[var(--risk-high-border)] m-4 rounded-[14px] flex items-center justify-center gap-2">
            <AlertTriangle className="w-4 h-4" />
            <span>Failed to load documents. Please ensure the backend service is reachable.</span>
          </div>
        ) : filteredDocs.length === 0 ? (
          <div className="p-12 text-center text-[var(--muted-foreground)] flex flex-col items-center">
            <div className="w-12 h-12 rounded-[14px] bg-[var(--soft-surface)] flex items-center justify-center mb-3 text-[var(--muted-foreground)]">
              <FileText className="w-6 h-6" />
            </div>
            <h3 className="font-serif text-sm font-semibold text-[var(--foreground)] mb-1">
              No Documents Found
            </h3>
            <p className="text-xs text-[var(--muted-foreground)] max-w-sm mb-5 leading-relaxed">
              {searchTerm
                ? `No agreements match "${searchTerm}". Try resetting your filter.`
                : "Upload your first legal document to begin clause extraction and benchmark risk analysis."}
            </p>
            <Link href="/upload">
              <Button size="sm">
                <UploadCloud className="w-3.5 h-3.5 mr-1" />
                <span>Upload Document</span>
              </Button>
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="text-[11px] font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--soft-surface)]/70 border-b border-[var(--border)]">
                <tr>
                  <th className="py-3 px-5">Document Name</th>
                  <th className="py-3 px-5">Category</th>
                  <th className="py-3 px-5">Risk Rating</th>
                  <th className="py-3 px-5">Status</th>
                  <th className="py-3 px-5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)]">
                {filteredDocs.map((doc) => {
                  const riskScore = doc.overall_risk_score;
                  let riskCategory = "standard";
                  if (riskScore !== null && riskScore !== undefined) {
                    if (riskScore >= 75) riskCategory = "high_risk";
                    else if (riskScore >= 50) riskCategory = "one_sided";
                    else if (riskScore >= 25) riskCategory = "slightly_unusual";
                  }

                  return (
                    <tr
                      key={doc.id}
                      className="hover:bg-[var(--soft-surface)]/40 transition-colors group"
                    >
                      <td className="py-3.5 px-5 font-medium text-[var(--foreground)]">
                        <div className="flex items-center gap-2.5">
                          <div className="w-7 h-7 rounded-[8px] bg-[var(--soft-surface)] border border-[var(--border)] flex items-center justify-center text-[var(--accent)] shrink-0">
                            <FileText className="w-3.5 h-3.5" />
                          </div>
                          <span className="truncate max-w-xs font-semibold">
                            {doc.original_filename}
                          </span>
                        </div>
                      </td>
                      <td className="py-3.5 px-5 text-[var(--muted-foreground)] capitalize">
                        {doc.document_type.replace(/_/g, " ")}
                      </td>
                      <td className="py-3.5 px-5">
                        {riskScore !== null && riskScore !== undefined ? (
                          <RiskChip category={riskCategory} score={riskScore} size="sm" />
                        ) : (
                          <span className="text-[var(--muted-foreground)] italic text-[11px]">Pending</span>
                        )}
                      </td>
                      <td className="py-3.5 px-5">
                        <StatusBadge status={doc.status} />
                      </td>
                      <td className="py-3.5 px-5 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <Link href={`/analysis/${doc.id}`}>
                            <Button variant="outline" size="sm" className="h-7 text-xs">
                              <span>Open</span>
                              <ArrowRight className="w-3 h-3 ml-1" />
                            </Button>
                          </Link>

                          {doc.status === "completed" && (
                            <button
                              type="button"
                              onClick={() => handleExport(doc.id, "markdown")}
                              aria-label={`Download Markdown export for ${doc.original_filename}`}
                              title="Download Markdown Report"
                              className="p-1.5 rounded-[8px] text-[var(--muted-foreground)] hover:text-[var(--foreground)] bg-[var(--card)] border border-[var(--border)] hover:bg-[var(--soft-surface)] transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--accent)]"
                            >
                              <Download className="w-3.5 h-3.5" />
                            </button>
                          )}

                          <button
                            type="button"
                            onClick={() => {
                              if (window.confirm(`Are you sure you want to delete "${doc.original_filename}"? This action cannot be undone.`)) {
                                deleteMutation.mutate(doc.id);
                              }
                            }}
                            aria-label={`Delete ${doc.original_filename}`}
                            title="Delete Document"
                            className="p-1.5 rounded-[8px] text-[var(--muted-foreground)] hover:text-[var(--risk-high-text)] bg-[var(--card)] border border-[var(--border)] hover:bg-[var(--risk-high-bg)] transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--accent)]"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

export default function DocumentsPage() {
  return (
    <Suspense
      fallback={
        <div className="p-12 text-center text-xs text-[var(--muted-foreground)] space-y-2">
          <div className="w-6 h-6 rounded-full border-2 border-[var(--accent)] border-t-transparent animate-spin mx-auto" />
          <p>Loading document repository...</p>
        </div>
      }
    >
      <DocumentsContent />
    </Suspense>
  );
}

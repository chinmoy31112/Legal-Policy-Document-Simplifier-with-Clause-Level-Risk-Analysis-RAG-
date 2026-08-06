"use client";

import Link from "next/link";
import { useState } from "react";
import { useDocuments, useDeleteDocument } from "@/hooks/use-documents";
import { StatusBadge } from "@/components/documents/status-badge";
import { Header } from "@/components/layout/header";
import {
  FileText,
  Trash2,
  ArrowRight,
  Upload,
  Search,
  Filter,
  Clock,
  ShieldCheck,
  Zap,
  AlertTriangle
} from "lucide-react";

export default function DocumentsPage() {
  const [page, setPage] = useState(1);
  const [searchTerm, setSearchTerm] = useState("");
  const { data, isLoading, isError } = useDocuments(page, 20);
  const deleteMutation = useDeleteDocument();

  const documents = data?.items || [];

  const filteredDocs = documents.filter((doc) =>
    doc.original_filename.toLowerCase().includes(searchTerm.toLowerCase()) ||
    doc.document_type.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <>
      <Header
        title="Document Repository"
        subtitle="Full archive of uploaded policy agreements, audited clauses, and risk metrics"
      />
      <div className="space-y-6">
        {/* Top Control Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 rounded-2xl bg-slate-900/90 border border-slate-800 shadow-xl">
          <div className="flex items-center gap-3">
            <div className="relative flex-1 sm:w-80">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                type="text"
                placeholder="Filter documents by name or type..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 text-xs rounded-xl bg-slate-950 border border-slate-800 text-slate-100 placeholder:text-slate-500 focus:border-emerald-500 focus:outline-none transition-all"
              />
            </div>
            <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs font-bold text-slate-400">
              <Filter className="w-3.5 h-3.5 text-emerald-400" />
              <span>{filteredDocs.length} Documents</span>
            </div>
          </div>

          <Link
            href="/upload"
            className="inline-flex items-center justify-center gap-2 px-5 py-2.5 text-xs font-bold uppercase tracking-wider text-slate-950 rounded-xl bg-gradient-to-r from-emerald-400 to-teal-400 hover:from-emerald-300 hover:to-teal-300 shadow-md shadow-emerald-500/20 transition-all duration-300 hover:scale-[1.02]"
          >
            <Upload className="w-3.5 h-3.5" />
            Upload New Document
          </Link>
        </div>

        {/* Documents Table View */}
        <div className="rounded-3xl bg-slate-900/90 border border-slate-800 overflow-hidden shadow-2xl">
          {isLoading ? (
            <div className="p-16 text-center text-slate-400 text-xs space-y-3">
              <div className="w-8 h-8 rounded-full border-2 border-emerald-400 border-t-transparent animate-spin mx-auto" />
              <p>Fetching legal document repository...</p>
            </div>
          ) : isError ? (
            <div className="p-12 text-center text-red-400 text-xs bg-red-500/10 border border-red-500/20 m-6 rounded-2xl flex items-center justify-center gap-2">
              <AlertTriangle className="w-4 h-4" />
              <span>Failed to load documents from database. Please ensure backend is running.</span>
            </div>
          ) : filteredDocs.length === 0 ? (
            <div className="p-16 text-center text-slate-400 flex flex-col items-center">
              <div className="w-16 h-16 rounded-2xl bg-slate-950 border border-slate-800 flex items-center justify-center mb-4 text-slate-500">
                <FileText className="w-8 h-8" />
              </div>
              <h3 className="text-base font-bold text-slate-200 mb-1">No Matching Documents Found</h3>
              <p className="text-xs text-slate-400 max-w-sm mb-6">
                {searchTerm
                  ? `No results matching "${searchTerm}". Try resetting your filter.`
                  : "Upload your first legal document to begin clause extraction and RAG risk benchmarking."}
              </p>
              <Link
                href="/upload"
                className="px-6 py-2.5 text-xs font-bold uppercase tracking-wider text-slate-950 rounded-xl bg-emerald-400 hover:bg-emerald-300 transition-all shadow-md shadow-emerald-500/20"
              >
                Upload Document
              </Link>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="text-[11px] font-bold uppercase tracking-wider text-slate-400 bg-slate-950/60 border-b border-slate-800">
                  <tr>
                    <th className="px-6 py-4">Document Title</th>
                    <th className="px-6 py-4">Category</th>
                    <th className="px-6 py-4">Analysis Status</th>
                    <th className="px-6 py-4">Date Uploaded</th>
                    <th className="px-6 py-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-medium">
                  {filteredDocs.map((doc) => (
                    <tr key={doc.id} className="hover:bg-slate-800/40 transition-colors">
                      <td className="px-6 py-4 text-slate-200 font-bold flex items-center gap-3">
                        <div className="w-9 h-9 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 shrink-0">
                          <FileText className="w-4 h-4" />
                        </div>
                        <div>
                          <div className="truncate max-w-xs font-heading text-sm text-slate-100">{doc.original_filename}</div>
                          <div className="text-[10px] text-slate-500 font-mono mt-0.5">ID: {doc.id.substring(0, 8)}...</div>
                        </div>
                      </td>
                      <td className="px-6 py-4 capitalize text-slate-300">
                        <span className="px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800 text-[11px]">
                          {doc.document_type.replace("_", " ")}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <StatusBadge status={doc.status} />
                      </td>
                      <td className="px-6 py-4 text-slate-400">
                        <div className="flex items-center gap-1.5">
                          <Clock className="w-3.5 h-3.5 text-slate-500" />
                          {new Date(doc.created_at).toLocaleDateString("en-US", {
                            month: "short",
                            day: "numeric",
                            year: "numeric",
                          })}
                        </div>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => {
                              if (confirm("Are you sure you want to delete this document and its clause analyses?")) {
                                deleteMutation.mutate(doc.id);
                              }
                            }}
                            disabled={deleteMutation.isPending}
                            className="p-2 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all"
                            title="Delete Document"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>

                          <Link
                            href={`/analysis/${doc.id}`}
                            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-bold text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 hover:bg-emerald-500/20 transition-all shadow-sm"
                          >
                            {doc.status === "completed" ? "View Analysis" : "View Status"}
                            <ArrowRight className="w-3.5 h-3.5" />
                          </Link>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

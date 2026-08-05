"use client";

/**
 * Documents list page.
 */

import { motion } from "framer-motion";
import { Header } from "@/components/layout/header";
import { FileText, Filter, SortAsc } from "lucide-react";

export default function DocumentsPage() {
  return (
    <>
      <Header title="Documents" subtitle="Manage your uploaded legal documents" />
      <div className="p-8">
        {/* Toolbar */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <button className="flex items-center gap-2 px-4 py-2 text-sm rounded-xl bg-[var(--bg-surface)] border border-[var(--border-primary)] text-[var(--text-secondary)] hover:text-white hover:bg-[var(--bg-elevated)] transition-all">
              <Filter className="w-4 h-4" />
              Filter
            </button>
            <button className="flex items-center gap-2 px-4 py-2 text-sm rounded-xl bg-[var(--bg-surface)] border border-[var(--border-primary)] text-[var(--text-secondary)] hover:text-white hover:bg-[var(--bg-elevated)] transition-all">
              <SortAsc className="w-4 h-4" />
              Sort
            </button>
          </div>
          <a
            href="/dashboard/upload"
            className="px-5 py-2.5 text-sm font-semibold text-white rounded-xl gradient-brand hover:opacity-90 transition-opacity"
          >
            Upload New
          </a>
        </div>

        {/* Empty state */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col items-center justify-center py-24 text-center rounded-2xl bg-[var(--bg-surface)] border border-[var(--border-primary)]"
        >
          <div className="w-16 h-16 rounded-2xl bg-blue-500/10 flex items-center justify-center mb-5">
            <FileText className="w-8 h-8 text-blue-400" />
          </div>
          <h3 className="text-lg font-semibold mb-2">No documents yet</h3>
          <p className="text-[var(--text-muted)] max-w-md">
            Your uploaded documents will appear here. Upload a legal document to
            get started.
          </p>
        </motion.div>
      </div>
    </>
  );
}

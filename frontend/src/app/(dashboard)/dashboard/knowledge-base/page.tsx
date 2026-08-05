"use client";

/**
 * Knowledge base management page.
 */

import { motion } from "framer-motion";
import { Header } from "@/components/layout/header";
import { Database, Upload, FileText } from "lucide-react";

export default function KnowledgeBasePage() {
  return (
    <>
      <Header
        title="Knowledge Base"
        subtitle="Manage reference clauses for RAG comparison"
      />
      <div className="p-8">
        <div className="flex items-center justify-between mb-6">
          <p className="text-sm text-[var(--text-muted)]">
            Reference documents used for clause comparison
          </p>
          <button className="flex items-center gap-2 px-5 py-2.5 text-sm font-semibold text-white rounded-xl gradient-brand hover:opacity-90 transition-opacity">
            <Upload className="w-4 h-4" />
            Upload Reference
          </button>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col items-center justify-center py-24 text-center rounded-2xl bg-[var(--bg-surface)] border border-[var(--border-primary)]"
        >
          <div className="w-16 h-16 rounded-2xl bg-teal-500/10 flex items-center justify-center mb-5">
            <Database className="w-8 h-8 text-teal-400" />
          </div>
          <h3 className="text-lg font-semibold mb-2">
            Knowledge base is empty
          </h3>
          <p className="text-[var(--text-muted)] max-w-md">
            Seed the knowledge base with reference clauses using the CLI or
            upload reference documents here.
          </p>
        </motion.div>
      </div>
    </>
  );
}

"use client";

/**
 * Analysis results page for a specific document.
 */

import { motion } from "framer-motion";
import { Header } from "@/components/layout/header";
import {
  FileText,
  Shield,
  AlertTriangle,
  ChevronRight,
  Eye,
} from "lucide-react";

export default function AnalysisPage() {
  return (
    <>
      <Header
        title="Document Analysis"
        subtitle="Clause-level risk analysis results"
      />
      <div className="p-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col items-center justify-center py-24 text-center rounded-2xl bg-[var(--bg-surface)] border border-[var(--border-primary)]"
        >
          <div className="w-16 h-16 rounded-2xl bg-purple-500/10 flex items-center justify-center mb-5">
            <Shield className="w-8 h-8 text-purple-400" />
          </div>
          <h3 className="text-lg font-semibold mb-2">
            No analysis selected
          </h3>
          <p className="text-[var(--text-muted)] max-w-md">
            Select a document from the documents page to view its clause-level
            risk analysis.
          </p>
        </motion.div>
      </div>
    </>
  );
}

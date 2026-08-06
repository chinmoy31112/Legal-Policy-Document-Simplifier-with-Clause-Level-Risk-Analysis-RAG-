"use client";

/**
 * Knowledge base management page.
 */

import { motion } from "framer-motion";
import { Header } from "@/components/layout/header";
import { Database, Upload } from "lucide-react";

export default function KnowledgeBasePage() {
  return (
    <>
      <Header
        title="Benchmark Knowledge Base"
        subtitle="Manage reference legal clauses used for RAG risk comparisons"
      />
      <div className="space-y-8">
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium text-[#74796e]">
            Standard benchmark agreements and clause definitions
          </p>
          <button className="flex items-center gap-2.5 px-7 py-3 text-sm font-semibold text-white rounded-full bg-[#55624d] hover:bg-[#45513d] shadow-ambient transition-all duration-300">
            <Upload className="w-4 h-4" />
            Upload Benchmark Reference
          </button>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col items-center justify-center py-24 text-center rounded-3xl bg-white shadow-ambient"
        >
          <div className="w-20 h-20 rounded-3xl bg-[#d9e7cd]/60 flex items-center justify-center mb-6 text-[#55624d] shadow-ambient">
            <Database className="w-10 h-10" />
          </div>
          <h3 className="text-xl font-bold font-display text-[#191c18] mb-2">
            Sanctuary Knowledge Base Seed
          </h3>
          <p className="text-[#74796e] max-w-md leading-relaxed text-sm">
            Seed standard clause definitions into your RAG store to compare uploaded agreements against legal benchmarks.
          </p>
        </motion.div>
      </div>
    </>
  );
}


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
      <Header title="My Documents" subtitle="Manage and review your uploaded legal agreements" />
      <div className="space-y-8">
        {/* Toolbar */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button className="flex items-center gap-2 px-4 py-2.5 text-sm font-semibold rounded-full bg-white text-[#444841] hover:bg-[#f2f4ed] shadow-ambient transition-all">
              <Filter className="w-4 h-4 text-[#55624d]" />
              Filter
            </button>
            <button className="flex items-center gap-2 px-4 py-2.5 text-sm font-semibold rounded-full bg-white text-[#444841] hover:bg-[#f2f4ed] shadow-ambient transition-all">
              <SortAsc className="w-4 h-4 text-[#55624d]" />
              Sort
            </button>
          </div>
          <a
            href="/dashboard/upload"
            className="px-7 py-3 text-sm font-semibold text-white rounded-full bg-[#55624d] hover:bg-[#45513d] shadow-ambient transition-all duration-300"
          >
            Upload New Agreement
          </a>
        </div>

        {/* Empty state */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col items-center justify-center py-24 text-center rounded-3xl bg-white shadow-ambient"
        >
          <div className="w-20 h-20 rounded-3xl bg-[#d9e7cd]/60 flex items-center justify-center mb-6 text-[#55624d] shadow-ambient">
            <FileText className="w-10 h-10" />
          </div>
          <h3 className="text-xl font-bold font-display text-[#191c18] mb-2">No documents in sanctuary</h3>
          <p className="text-[#74796e] max-w-md leading-relaxed text-sm">
            Your uploaded documents and clause analyses will be organized here.
          </p>
        </motion.div>
      </div>
    </>
  );
}


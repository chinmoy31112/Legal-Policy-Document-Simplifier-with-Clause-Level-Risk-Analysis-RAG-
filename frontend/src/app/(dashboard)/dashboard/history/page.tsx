"use client";

/**
 * Analysis history page.
 */

import { motion } from "framer-motion";
import { Header } from "@/components/layout/header";
import { History } from "lucide-react";

export default function HistoryPage() {
  return (
    <>
      <Header title="Analysis History Log" subtitle="Chronological transcript of your evaluated documents" />
      <div className="space-y-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col items-center justify-center py-24 text-center rounded-3xl bg-white shadow-ambient"
        >
          <div className="w-20 h-20 rounded-3xl bg-[#fef3c7]/60 flex items-center justify-center mb-6 text-[#b45309] shadow-ambient">
            <History className="w-10 h-10" />
          </div>
          <h3 className="text-xl font-bold font-display text-[#191c18] mb-2">No past history</h3>
          <p className="text-[#74796e] max-w-md leading-relaxed text-sm">
            Your completed clause analysis records will be stored here.
          </p>
        </motion.div>
      </div>
    </>
  );
}


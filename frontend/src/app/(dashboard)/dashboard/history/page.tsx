"use client";

/**
 * Analysis history page.
 */

import { motion } from "framer-motion";
import { Header } from "@/components/layout/header";
import { History, Clock } from "lucide-react";

export default function HistoryPage() {
  return (
    <>
      <Header title="History" subtitle="View past document analyses" />
      <div className="p-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col items-center justify-center py-24 text-center rounded-2xl bg-[var(--bg-surface)] border border-[var(--border-primary)]"
        >
          <div className="w-16 h-16 rounded-2xl bg-amber-500/10 flex items-center justify-center mb-5">
            <History className="w-8 h-8 text-amber-400" />
          </div>
          <h3 className="text-lg font-semibold mb-2">No history yet</h3>
          <p className="text-[var(--text-muted)] max-w-md">
            Your completed analyses will appear here as a chronological log.
          </p>
        </motion.div>
      </div>
    </>
  );
}

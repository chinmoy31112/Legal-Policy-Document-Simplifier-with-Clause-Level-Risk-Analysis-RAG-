"use client";

/**
 * Dashboard home page — overview of recent documents and stats.
 */

import { motion } from "framer-motion";
import { Header } from "@/components/layout/header";
import {
  FileText,
  Shield,
  AlertTriangle,
  CheckCircle2,
  TrendingUp,
  Clock,
} from "lucide-react";

const stats = [
  {
    label: "Total Documents",
    value: "—",
    icon: FileText,
    color: "text-blue-400",
    bg: "bg-blue-500/10",
  },
  {
    label: "Analyzed",
    value: "—",
    icon: CheckCircle2,
    color: "text-emerald-400",
    bg: "bg-emerald-500/10",
  },
  {
    label: "High Risk Found",
    value: "—",
    icon: AlertTriangle,
    color: "text-red-400",
    bg: "bg-red-500/10",
  },
  {
    label: "Avg. Risk Score",
    value: "—",
    icon: TrendingUp,
    color: "text-yellow-400",
    bg: "bg-yellow-500/10",
  },
];

const fadeIn = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
};

export default function DashboardPage() {
  return (
    <>
      <Header title="Dashboard" subtitle="Overview of your document analyses" />
      <div className="p-8 space-y-8">
        {/* Stats Grid */}
        <motion.div
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5"
          initial="hidden"
          animate="visible"
          variants={{
            visible: { transition: { staggerChildren: 0.08 } },
          }}
        >
          {stats.map((stat) => {
            const Icon = stat.icon;
            return (
              <motion.div
                key={stat.label}
                variants={fadeIn}
                transition={{ duration: 0.4 }}
                className="p-6 rounded-2xl bg-[var(--bg-surface)] border border-[var(--border-primary)] hover:border-[var(--border-primary)] hover:bg-[var(--bg-elevated)] transition-all group"
              >
                <div className="flex items-center justify-between mb-4">
                  <div
                    className={`w-10 h-10 rounded-xl ${stat.bg} flex items-center justify-center`}
                  >
                    <Icon className={`w-5 h-5 ${stat.color}`} />
                  </div>
                </div>
                <p className="text-3xl font-bold">{stat.value}</p>
                <p className="text-sm text-[var(--text-muted)] mt-1">
                  {stat.label}
                </p>
              </motion.div>
            );
          })}
        </motion.div>

        {/* Recent Activity */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4, duration: 0.5 }}
          className="rounded-2xl bg-[var(--bg-surface)] border border-[var(--border-primary)] p-6"
        >
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold">Recent Documents</h2>
            <button className="text-sm text-blue-400 hover:text-blue-300 transition-colors">
              View All
            </button>
          </div>

          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="w-16 h-16 rounded-2xl bg-blue-500/10 flex items-center justify-center mb-5">
              <FileText className="w-8 h-8 text-blue-400" />
            </div>
            <h3 className="text-lg font-semibold mb-2">No documents yet</h3>
            <p className="text-[var(--text-muted)] max-w-md">
              Upload your first legal document to see AI-powered clause analysis
              with risk assessment.
            </p>
            <a
              href="/dashboard/upload"
              className="mt-6 inline-flex items-center gap-2 px-6 py-2.5 text-sm font-semibold text-white rounded-xl gradient-brand hover:opacity-90 transition-opacity"
            >
              Upload Document
            </a>
          </div>
        </motion.div>

        {/* Quick Guide */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5, duration: 0.5 }}
          className="grid grid-cols-1 md:grid-cols-3 gap-5"
        >
          {[
            {
              step: "01",
              title: "Upload Document",
              desc: "Upload a PDF, DOCX, or TXT legal document.",
              icon: FileText,
            },
            {
              step: "02",
              title: "AI Analysis",
              desc: "Our RAG pipeline analyzes every clause against standard benchmarks.",
              icon: Shield,
            },
            {
              step: "03",
              title: "Review Results",
              desc: "Get risk scores, plain-English summaries, and suggested rewrites.",
              icon: CheckCircle2,
            },
          ].map((item) => {
            const Icon = item.icon;
            return (
              <div
                key={item.step}
                className="p-6 rounded-2xl bg-[var(--bg-surface)] border border-[var(--border-primary)] group hover:bg-[var(--bg-elevated)] transition-all"
              >
                <span className="text-xs font-bold text-blue-400 tracking-wider">
                  STEP {item.step}
                </span>
                <h3 className="text-base font-semibold mt-2 mb-2">
                  {item.title}
                </h3>
                <p className="text-sm text-[var(--text-muted)]">{item.desc}</p>
              </div>
            );
          })}
        </motion.div>
      </div>
    </>
  );
}

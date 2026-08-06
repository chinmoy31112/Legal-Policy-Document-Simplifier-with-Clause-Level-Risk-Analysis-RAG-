"use client";

import { motion } from "framer-motion";
import { Header } from "@/components/layout/header";
import { useDocuments } from "@/hooks/use-documents";
import { StatusBadge } from "@/components/documents/status-badge";
import Link from "next/link";
import {
  FileText,
  Shield,
  AlertTriangle,
  CheckCircle2,
  TrendingUp,
  Upload,
  ArrowRight,
  Sparkles,
  Zap,
  Clock
} from "lucide-react";

const fadeIn = {
  hidden: { opacity: 0, y: 15 },
  visible: { opacity: 1, y: 0 },
};

export default function DashboardPage() {
  const { data: docsData, isLoading } = useDocuments(1, 10);
  const documents = docsData?.items || [];
  const totalDocs = docsData?.total || 0;

  const completedDocs = documents.filter((d) => d.status === "completed").length;
  const analyzingDocs = documents.filter((d) =>
    ["uploaded", "extracting", "segmenting", "analyzing"].includes(d.status)
  ).length;

  const stats = [
    {
      label: "Total Documents",
      value: totalDocs.toString(),
      subtext: "Indexed in repository",
      icon: FileText,
      color: "text-emerald-400",
      glow: "border-emerald-500/30 bg-emerald-500/5",
    },
    {
      label: "Completed Analysis",
      value: completedDocs.toString(),
      subtext: "Fully processed & benchmarked",
      icon: CheckCircle2,
      color: "text-teal-400",
      glow: "border-teal-500/30 bg-teal-500/5",
    },
    {
      label: "In Active Analysis",
      value: analyzingDocs.toString(),
      subtext: "RAG processing queue",
      icon: Zap,
      color: "text-indigo-400",
      glow: "border-indigo-500/30 bg-indigo-500/5",
    },
    {
      label: "RAG Reference Engine",
      value: "Standard-v2",
      subtext: "Google Gemini 3.5 Active",
      icon: Shield,
      color: "text-cyan-400",
      glow: "border-cyan-500/30 bg-cyan-500/5",
    },
  ];

  return (
    <>
      <Header
        title="Policy & Contract Intelligence Dashboard"
        subtitle="Real-time clause-level risk quantification and automated legal simplification"
      />
      <div className="space-y-8">
        {/* Metric Cards Grid */}
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
                transition={{ duration: 0.3 }}
                className={`p-6 rounded-2xl border ${stat.glow} backdrop-blur-xl relative overflow-hidden group hover:border-emerald-500/50 transition-all duration-300`}
              >
                <div className="flex items-center justify-between mb-4">
                  <div className="w-10 h-10 rounded-xl bg-slate-900/80 border border-slate-800 flex items-center justify-center">
                    <Icon className={`w-5 h-5 ${stat.color}`} />
                  </div>
                  <span className="text-[10px] font-bold tracking-widest text-slate-500 uppercase">
                    LIVE METRIC
                  </span>
                </div>
                <h3 className="text-3xl font-extrabold font-heading text-slate-100 tracking-tight">
                  {stat.value}
                </h3>
                <p className="text-xs font-semibold text-slate-300 mt-1">
                  {stat.label}
                </p>
                <p className="text-[11px] text-slate-500 mt-0.5">{stat.subtext}</p>
              </motion.div>
            );
          })}
        </motion.div>

        {/* Action Hero & Quick Upload Launcher */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <motion.div
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="lg:col-span-2 p-8 rounded-3xl bg-gradient-to-br from-slate-900 via-[#0d1527] to-slate-900 border border-slate-800 relative overflow-hidden shadow-2xl flex flex-col justify-between"
          >
            <div className="absolute top-0 right-0 w-96 h-96 bg-emerald-500/10 blur-[100px] rounded-full pointer-events-none" />
            <div className="relative z-10 space-y-4">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-bold">
                <Sparkles className="w-3.5 h-3.5" />
                <span>Next-Gen RAG Analysis Engine</span>
              </div>
              <h2 className="text-2xl lg:text-3xl font-extrabold font-heading text-white tracking-tight leading-tight">
                Analyze Legal Contracts & Policies with Clause-Level Precision
              </h2>
              <p className="text-slate-400 text-sm max-w-xl leading-relaxed">
                Upload NDA, Terms of Service, Privacy Policies, or Government Regulations.
                Our engine extracts clauses, queries benchmark databases, and identifies high-risk terms instantly.
              </p>
            </div>

            <div className="relative z-10 pt-8 flex flex-wrap items-center gap-4">
              <Link
                href="/upload"
                className="inline-flex items-center gap-2.5 px-6 py-3 text-xs font-bold uppercase tracking-wider text-slate-950 rounded-xl bg-gradient-to-r from-emerald-400 to-teal-400 hover:from-emerald-300 hover:to-teal-300 shadow-lg shadow-emerald-500/20 transition-all duration-300 hover:scale-[1.02]"
              >
                <Upload className="w-4 h-4" />
                Upload New Document
              </Link>
              <Link
                href="/documents"
                className="inline-flex items-center gap-2 px-5 py-3 text-xs font-bold uppercase tracking-wider text-slate-300 rounded-xl bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 transition-all duration-300"
              >
                Browse Repository <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </motion.div>

          {/* Quick RAG Workflow Steps Card */}
          <motion.div
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="p-7 rounded-3xl bg-slate-900/90 border border-slate-800 flex flex-col justify-between"
          >
            <div>
              <h3 className="text-base font-bold font-heading text-slate-200 mb-4 flex items-center gap-2">
                <Zap className="w-4 h-4 text-emerald-400" /> Executive Workflow
              </h3>
              <div className="space-y-4">
                {[
                  { step: "01", title: "Document Upload", desc: "PDF, DOCX, TXT parsing with OCR support." },
                  { step: "02", title: "Clause Segmentation", desc: "Rule-based & AI text block extraction." },
                  { step: "03", title: "Vector Search Benchmark", desc: "Cosine similarity lookup against legal standard KB." },
                  { step: "04", title: "LLM Risk Quantification", desc: "Structured output with plain-English rewrites." },
                ].map((item) => (
                  <div key={item.step} className="flex items-start gap-3">
                    <span className="w-6 h-6 rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 text-xs font-bold flex items-center justify-center shrink-0">
                      {item.step}
                    </span>
                    <div>
                      <div className="text-xs font-bold text-slate-200">{item.title}</div>
                      <div className="text-[11px] text-slate-400 mt-0.5">{item.desc}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        </div>

        {/* Recent Documents Table */}
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="rounded-3xl bg-slate-900/90 border border-slate-800 overflow-hidden shadow-xl"
        >
          <div className="p-6 border-b border-slate-800 flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold font-heading text-slate-100">Recent Analyzed Documents</h2>
              <p className="text-xs text-slate-400 mt-0.5">Latest policy analyses and agreement audits</p>
            </div>
            <Link
              href="/documents"
              className="text-xs font-bold text-emerald-400 hover:text-emerald-300 flex items-center gap-1.5 transition-all"
            >
              View All Documents <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          {isLoading ? (
            <div className="p-12 text-center text-slate-400 text-xs space-y-3">
              <div className="w-8 h-8 rounded-full border-2 border-emerald-400 border-t-transparent animate-spin mx-auto" />
              <p>Loading document repository...</p>
            </div>
          ) : documents.length === 0 ? (
            <div className="p-12 text-center text-slate-400 flex flex-col items-center">
              <div className="w-16 h-16 rounded-2xl bg-slate-800/80 border border-slate-700 flex items-center justify-center mb-4">
                <FileText className="w-8 h-8 text-slate-500" />
              </div>
              <h3 className="text-base font-bold text-slate-200 mb-1">No Documents in Repository</h3>
              <p className="text-xs text-slate-400 max-w-sm mb-6">
                Upload your first legal document or contract to start automated RAG clause-level risk assessment.
              </p>
              <Link
                href="/upload"
                className="px-6 py-2.5 text-xs font-bold uppercase tracking-wider text-slate-950 rounded-xl bg-emerald-400 hover:bg-emerald-300 transition-all shadow-md shadow-emerald-500/20"
              >
                Upload First Document
              </Link>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="text-[11px] font-bold uppercase tracking-wider text-slate-400 bg-slate-950/50 border-b border-slate-800">
                  <tr>
                    <th className="px-6 py-4">Document Title</th>
                    <th className="px-6 py-4">Document Type</th>
                    <th className="px-6 py-4">Status</th>
                    <th className="px-6 py-4">Upload Date</th>
                    <th className="px-6 py-4 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-medium">
                  {documents.map((doc) => (
                    <tr key={doc.id} className="hover:bg-slate-800/40 transition-colors">
                      <td className="px-6 py-4 text-slate-200 font-bold flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 shrink-0">
                          <FileText className="w-4 h-4" />
                        </div>
                        <span className="truncate max-w-xs">{doc.original_filename}</span>
                      </td>
                      <td className="px-6 py-4 capitalize text-slate-300">
                        {doc.document_type.replace("_", " ")}
                      </td>
                      <td className="px-6 py-4">
                        <StatusBadge status={doc.status} />
                      </td>
                      <td className="px-6 py-4 text-slate-400 flex items-center gap-1.5">
                        <Clock className="w-3.5 h-3.5 text-slate-500" />
                        {new Date(doc.created_at).toLocaleDateString("en-US", {
                          month: "short",
                          day: "numeric",
                          year: "numeric",
                        })}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <Link
                          href={`/analysis/${doc.id}`}
                          className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-bold text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 hover:bg-emerald-500/20 transition-all"
                        >
                          {doc.status === "completed" ? "View Analysis" : "View Status"}
                          <ArrowRight className="w-3.5 h-3.5" />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </motion.div>
      </div>
    </>
  );
}

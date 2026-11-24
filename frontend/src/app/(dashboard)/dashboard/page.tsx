"use client";

import { motion } from "framer-motion";
import { useDocuments } from "@/hooks/use-documents";
import { StatusBadge } from "@/components/documents/status-badge";
import { RiskChip } from "@/components/ui/risk-chip";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import {
  FileText,
  Shield,
  CheckCircle2,
  UploadCloud,
  ArrowRight,
  Zap,
  Sparkles,
} from "lucide-react";

const fadeIn = {
  hidden: { opacity: 0, y: 8 },
  visible: { opacity: 1, y: 0 },
};

export default function DashboardPage() {
  const { data: docsData, isLoading } = useDocuments(1, 10);
  const documents = docsData?.items || [];
  const totalDocs = docsData?.total || 0;

  const completedDocs = documents.filter((d) => d.status === "completed").length;
  const analyzingDocs = documents.filter((d) =>
    ["uploaded", "extracting", "segmenting", "analyzing", "waiting for quota"].includes(d.status)
  ).length;

  const stats = [
    {
      label: "Total Documents",
      value: totalDocs.toString(),
      subtext: "Repository agreements",
      icon: FileText,
    },
    {
      label: "Completed Analysis",
      value: completedDocs.toString(),
      subtext: "Benchmarked & simplified",
      icon: CheckCircle2,
    },
    {
      label: "Processing Queue",
      value: analyzingDocs.toString(),
      subtext: "Active RAG pipeline",
      icon: Zap,
    },
    {
      label: "AI Reasoning Tier",
      value: "Gemini 3.5",
      subtext: "Flash-Lite (Pinned)",
      icon: Shield,
    },
  ];

  return (
    <div className="space-y-6 select-none max-w-6xl mx-auto">
      {/* Page Header */}
      <div>
        <h1 className="font-serif text-2xl font-semibold text-[var(--foreground)] tracking-tight">
          Contract & Policy Intelligence
        </h1>
        <p className="text-xs text-[var(--muted-foreground)] mt-1">
          Automated clause segmentation, RAG benchmark retrieval, and objective risk scoring
        </p>
      </div>

      {/* Metric Cards Grid */}
      <motion.div
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"
        initial="hidden"
        animate="visible"
        variants={{
          visible: { transition: { staggerChildren: 0.05 } },
        }}
      >
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <motion.div
              key={stat.label}
              variants={fadeIn}
              transition={{ duration: 0.2 }}
              className="p-5 rounded-[18px] border border-[var(--border)] bg-[var(--card)] shadow-none space-y-2"
            >
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-semibold tracking-wider text-[var(--muted-foreground)] uppercase">
                  {stat.label}
                </span>
                <div className="w-8 h-8 rounded-[8px] bg-[var(--soft-surface)] border border-[var(--border)] flex items-center justify-center text-[var(--accent)]">
                  <Icon className="w-4 h-4" />
                </div>
              </div>
              <div className="font-serif text-2xl font-bold text-[var(--foreground)] tabular-nums">
                {stat.value}
              </div>
              <div className="text-[11px] text-[var(--muted-foreground)]">
                {stat.subtext}
              </div>
            </motion.div>
          );
        })}
      </motion.div>

      {/* Quick Launch Action Banner */}
      <div className="p-6 rounded-[18px] bg-[var(--soft-surface)] border border-[var(--border)] flex flex-col md:flex-row items-start md:items-center justify-between gap-5">
        <div className="space-y-1.5 max-w-xl">
          <div className="inline-flex items-center gap-1.5 text-xs font-semibold text-[var(--accent)]">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Instant Agreement Analysis</span>
          </div>
          <h3 className="font-serif text-base font-semibold text-[var(--foreground)]">
            Analyze a Contract, Terms of Service, or Privacy Policy
          </h3>
          <p className="text-xs text-[var(--muted-foreground)] leading-relaxed">
            Upload your agreement to extract clauses, query the 200 standard commercial precedents in PostgreSQL pgvector, and generate plain English simplifications.
          </p>
        </div>

        <Link href="/upload">
          <Button size="lg" className="shrink-0">
            <UploadCloud className="w-4 h-4 mr-1.5" />
            <span>Upload Agreement</span>
          </Button>
        </Link>
      </div>

      {/* Recent Documents Section */}
      <div className="rounded-[18px] bg-[var(--card)] border border-[var(--border)] overflow-hidden shadow-none">
        <div className="p-5 border-b border-[var(--border)] flex items-center justify-between">
          <div>
            <h3 className="font-serif text-base font-semibold text-[var(--foreground)]">
              Recent Documents
            </h3>
            <p className="text-xs text-[var(--muted-foreground)] mt-0.5">
              Access clause-by-clause risk breakdowns and synchronized viewer
            </p>
          </div>
          <Link
            href="/documents"
            className="text-xs font-medium text-[var(--accent)] hover:opacity-80 flex items-center gap-1 transition-opacity"
          >
            <span>View All ({totalDocs})</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {isLoading ? (
          <div className="p-12 text-center space-y-3 text-[var(--muted-foreground)] text-xs">
            <div className="w-7 h-7 rounded-full border-2 border-[var(--accent)] border-t-transparent animate-spin mx-auto" />
            <p>Loading documents...</p>
          </div>
        ) : documents.length === 0 ? (
          <div className="p-12 text-center space-y-3">
            <div className="w-12 h-12 rounded-[14px] bg-[var(--soft-surface)] flex items-center justify-center mx-auto text-[var(--muted-foreground)]">
              <FileText className="w-6 h-6" />
            </div>
            <div className="space-y-1">
              <h4 className="font-serif text-sm font-semibold text-[var(--foreground)]">No Documents Uploaded Yet</h4>
              <p className="text-xs text-[var(--muted-foreground)] max-w-sm mx-auto">
                Get started by uploading your first contract PDF, terms of service, or privacy policy.
              </p>
            </div>
            <Link href="/upload">
              <Button size="sm">
                <UploadCloud className="w-3.5 h-3.5 mr-1" />
                <span>Upload First Agreement</span>
              </Button>
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="text-[11px] font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--soft-surface)]/70 border-b border-[var(--border)]">
                <tr>
                  <th className="py-3 px-5">Document Name</th>
                  <th className="py-3 px-5">Category</th>
                  <th className="py-3 px-5">Risk Rating</th>
                  <th className="py-3 px-5">Status</th>
                  <th className="py-3 px-5 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)]">
                {documents.map((doc) => {
                  const riskScore = doc.overall_risk_score;
                  let riskCategory = "standard";
                  if (riskScore !== null && riskScore !== undefined) {
                    if (riskScore >= 75) riskCategory = "high_risk";
                    else if (riskScore >= 50) riskCategory = "one_sided";
                    else if (riskScore >= 25) riskCategory = "slightly_unusual";
                  }

                  return (
                    <tr
                      key={doc.id}
                      className="hover:bg-[var(--soft-surface)]/40 transition-colors group"
                    >
                      <td className="py-3.5 px-5 font-medium text-[var(--foreground)]">
                        <div className="flex items-center gap-2.5">
                          <div className="w-7 h-7 rounded-[8px] bg-[var(--soft-surface)] border border-[var(--border)] flex items-center justify-center text-[var(--accent)] shrink-0">
                            <FileText className="w-3.5 h-3.5" />
                          </div>
                          <span className="truncate max-w-xs font-semibold">
                            {doc.original_filename}
                          </span>
                        </div>
                      </td>
                      <td className="py-3.5 px-5 text-[var(--muted-foreground)] capitalize">
                        {doc.document_type.replace(/_/g, " ")}
                      </td>
                      <td className="py-3.5 px-5">
                        {riskScore !== null && riskScore !== undefined ? (
                          <RiskChip category={riskCategory} score={riskScore} size="sm" />
                        ) : (
                          <span className="text-[var(--muted-foreground)] italic text-[11px]">Pending</span>
                        )}
                      </td>
                      <td className="py-3.5 px-5">
                        <StatusBadge status={doc.status} />
                      </td>
                      <td className="py-3.5 px-5 text-right">
                        <Link href={`/analysis/${doc.id}`}>
                          <Button variant="outline" size="sm" className="h-7 text-xs">
                            <span>Review</span>
                            <ArrowRight className="w-3 h-3 ml-1" />
                          </Button>
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

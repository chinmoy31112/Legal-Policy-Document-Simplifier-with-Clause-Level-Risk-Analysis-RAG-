"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import {
  FileSearch,
  Zap,
  ArrowRight,
  Brain,
  Sparkles,
  Scale,
  FileText,
  ShieldAlert,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme/theme-toggle";

const features = [
  {
    icon: FileSearch,
    title: "Structural Clause Segmentation",
    description:
      "Decomposes complex PDFs, DOCX, and TXT agreements into discrete legal provisions with exact character spans.",
  },
  {
    icon: Brain,
    title: "RAG Reference Grounding",
    description:
      "Retrieves verified standard clauses from a curated commercial benchmark before LLM reasoning for maximum precision.",
  },
  {
    icon: ShieldAlert,
    title: "Objective Risk Quantification",
    description:
      "Classifies each clause across Standard, Slightly Unusual, One-Sided, and High-Risk tiers with actionable negotiation notes.",
  },
  {
    icon: Zap,
    title: "Plain-English Simplification",
    description:
      "Translates opaque legalese into concise executive briefings with balanced neutral alternative rewrites for high-risk provisions.",
  },
];

const metrics = [
  { label: "High-Risk Recall", value: "93.3%", desc: "Catches asymmetric liabilities" },
  { label: "Reading Ease", value: "Grade 4.3", desc: "Down from postgraduate legalese" },
  { label: "Injection Defense", value: "100%", desc: "Cryptographic prompt boundaries" },
  { label: "Vector Reuse", value: "0-Cost", desc: "Shared multi-doc SHA-256 cache" },
];

const fadeInUp = {
  hidden: { opacity: 0, y: 12 },
  visible: { opacity: 1, y: 0 },
};

export default function LandingPage() {
  return (
    <div className="min-h-screen relative overflow-hidden bg-[var(--background)] text-[var(--foreground)] font-sans select-none">
      {/* Navigation Header */}
      <header className="fixed top-4 left-0 right-0 z-50 px-4 sm:px-6 max-w-6xl mx-auto">
        <nav className="p-3 sm:p-4 px-5 sm:px-6 rounded-[18px] bg-[var(--card)]/90 backdrop-blur-md flex items-center justify-between shadow-xs border border-[var(--border)]">
          <Link href="/" className="flex items-center gap-2.5 group">
            <div className="w-8 h-8 rounded-[10px] bg-[var(--accent)] flex items-center justify-center text-[var(--accent-foreground)] shadow-xs transition-transform duration-150 group-hover:scale-105">
              <FileText className="w-4 h-4" />
            </div>
            <div className="font-serif text-lg font-semibold tracking-tight text-[var(--foreground)]">
              LegalLens AI
            </div>
          </Link>

          <div className="flex items-center gap-2.5 sm:gap-3">
            <ThemeToggle />
            <Link href="/login">
              <Button variant="ghost" size="sm">
                Sign In
              </Button>
            </Link>
            <Link href="/dashboard">
              <Button size="sm">
                Launch Workspace
              </Button>
            </Link>
          </div>
        </nav>
      </header>

      {/* Hero Section */}
      <main className="relative z-10 pt-28 sm:pt-36">
        <section className="max-w-6xl mx-auto px-4 sm:px-6 pt-12 pb-20">
          <motion.div
            className="text-center max-w-3xl mx-auto space-y-6"
            initial="hidden"
            animate="visible"
            variants={{
              visible: { transition: { staggerChildren: 0.08 } },
            }}
          >
            <motion.div
              variants={fadeInUp}
              className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-[var(--soft-surface)] border border-[var(--border)] text-[var(--accent)] text-xs font-semibold shadow-xs"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Production Legal RAG • Clause-by-Clause Risk Analysis</span>
            </motion.div>

            <motion.h1
              variants={fadeInUp}
              className="font-serif text-3xl sm:text-5xl lg:text-6xl font-semibold tracking-tight leading-[1.15] text-[var(--foreground)]"
            >
              Understand Any Contract in{" "}
              <span className="text-[var(--accent)]">Seconds</span>, Not Hours.
            </motion.h1>

            <motion.p
              variants={fadeInUp}
              className="text-sm sm:text-base text-[var(--muted-foreground)] max-w-2xl mx-auto leading-relaxed"
            >
              Clause-level risk analysis, automated plain-English simplifications, and grounded commercial benchmark citations. Never get caught by unexpected liabilities again.
            </motion.p>

            <motion.div
              variants={fadeInUp}
              className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2"
            >
              <Link href="/upload" className="w-full sm:w-auto">
                <Button size="lg" className="w-full sm:w-auto">
                  <span>Analyze Your Contract</span>
                  <ArrowRight className="w-4 h-4 ml-1" />
                </Button>
              </Link>
              <Link href="/dashboard" className="w-full sm:w-auto">
                <Button variant="outline" size="lg" className="w-full sm:w-auto">
                  <span>Explore Dashboard</span>
                </Button>
              </Link>
            </motion.div>
          </motion.div>

          {/* Metric Bar */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-16 max-w-4xl mx-auto">
            {metrics.map((m) => (
              <div
                key={m.label}
                className="p-4 sm:p-5 rounded-[18px] bg-[var(--card)] border border-[var(--border)] text-center space-y-1"
              >
                <div className="font-serif text-2xl sm:text-3xl font-bold text-[var(--accent)]">
                  {m.value}
                </div>
                <div className="text-xs font-semibold text-[var(--foreground)]">{m.label}</div>
                <div className="text-[11px] text-[var(--muted-foreground)]">{m.desc}</div>
              </div>
            ))}
          </div>
        </section>

        {/* Feature Cards Grid */}
        <section className="max-w-6xl mx-auto px-4 sm:px-6 py-16 border-t border-[var(--border)]">
          <div className="text-center max-w-2xl mx-auto mb-12 space-y-2">
            <h2 className="font-serif text-2xl sm:text-3xl font-semibold text-[var(--foreground)]">
              Built on Enterprise Legal Guardrails
            </h2>
            <p className="text-xs sm:text-sm text-[var(--muted-foreground)] leading-relaxed">
              Every clause is verified through strict sequential processing: benchmark retrieval before reasoning, evidence grounding, and zero-prompt leakage.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
            {features.map((feature, i) => {
              const Icon = feature.icon;
              return (
                <div
                  key={i}
                  className="p-5 rounded-[18px] bg-[var(--card)] border border-[var(--border)] space-y-3"
                >
                  <div className="w-10 h-10 rounded-[10px] bg-[var(--soft-surface)] border border-[var(--border)] flex items-center justify-center text-[var(--accent)]">
                    <Icon className="w-5 h-5" />
                  </div>
                  <h3 className="font-serif text-base font-semibold text-[var(--foreground)]">
                    {feature.title}
                  </h3>
                  <p className="text-xs text-[var(--muted-foreground)] leading-relaxed">
                    {feature.description}
                  </p>
                </div>
              );
            })}
          </div>
        </section>

        {/* Legal Notice & Footer */}
        <footer className="border-t border-[var(--border)] bg-[var(--card)] py-10 px-4 sm:px-6">
          <div className="max-w-6xl mx-auto space-y-5">
            <div
              role="note"
              aria-label="Legal Notice"
              className="p-3.5 rounded-[14px] bg-[var(--soft-surface)] border border-[var(--border)] text-xs text-[var(--muted-foreground)] flex items-start gap-2.5"
            >
              <Scale className="w-4 h-4 text-[var(--accent)] shrink-0 mt-0.5" />
              <p className="leading-relaxed">
                <strong className="text-[var(--foreground)]">Statutory Notice:</strong> This platform provides automated document simplification and risk analysis for informational assistance only. It does not provide legal advice, legal opinions, or attorney recommendations. Always consult a qualified attorney before executing binding contracts.
              </p>
            </div>

            <div className="flex flex-col sm:flex-row items-center justify-between text-xs text-[var(--muted-foreground)] gap-3 pt-2">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-[var(--accent)]" />
                <span className="font-semibold text-[var(--foreground)]">LegalLens AI</span>
                <span>• MIT Licensed</span>
              </div>
              <div className="flex items-center gap-5">
                <Link href="/login" className="hover:text-[var(--foreground)] transition-colors">Sign In</Link>
                <Link href="/register" className="hover:text-[var(--foreground)] transition-colors">Create Account</Link>
                <Link href="/dashboard" className="hover:text-[var(--foreground)] transition-colors">Workspace</Link>
              </div>
            </div>
          </div>
        </footer>
      </main>
    </div>
  );
}

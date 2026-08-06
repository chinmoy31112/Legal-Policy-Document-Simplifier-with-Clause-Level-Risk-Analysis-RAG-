"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import {
  Shield,
  FileSearch,
  Zap,
  ArrowRight,
  CheckCircle2,
  Brain,
  Sparkles,
  Lock
} from "lucide-react";

const features = [
  {
    icon: FileSearch,
    title: "Automated Clause Extraction",
    description:
      "Detects and segments legal provisions from PDFs (with PyMuPDF OCR fallback), DOCX, and TXT files into clean analyzed clauses.",
  },
  {
    icon: Brain,
    title: "RAG Knowledge Base Benchmarking",
    description:
      "Queries vector databases to benchmark contract terms against verified standard legal precedents and regulatory baselines.",
  },
  {
    icon: Shield,
    title: "0-100 Risk Quantification",
    description:
      "Categorizes clauses across Standard, Slightly Unusual, One-Sided, High Risk, and Potentially Unenforceable spectrums.",
  },
  {
    icon: Zap,
    title: "Plain-English Simplification",
    description:
      "Translates opaque legalese into clear executive summaries alongside suggested balanced rewrites.",
  },
];

const fadeInUp = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
};

export default function LandingPage() {
  return (
    <div className="min-h-screen relative overflow-hidden bg-[#070a11] text-slate-100 font-sans">
      {/* Background Ambient Glows */}
      <div className="fixed inset-0 -z-10 pointer-events-none overflow-hidden">
        <div className="absolute top-[-10%] left-[20%] w-[600px] h-[600px] rounded-full bg-emerald-500/10 blur-[150px]" />
        <div className="absolute top-[40%] right-[-10%] w-[700px] h-[700px] rounded-full bg-indigo-500/10 blur-[180px]" />
      </div>

      {/* Navigation Header */}
      <header className="fixed top-6 left-0 right-0 z-50 px-6 max-w-7xl mx-auto">
        <nav className="p-4 px-8 rounded-2xl glass-panel flex items-center justify-between shadow-2xl border border-slate-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl gradient-emerald flex items-center justify-center shadow-lg shadow-emerald-500/20 text-white">
              <Shield className="w-5 h-5" />
            </div>
            <span className="text-xl font-bold font-heading tracking-tight text-white">
              GovLegal <span className="gradient-text-emerald">AI</span>
            </span>
          </div>
          <div className="flex items-center gap-4">
            <Link
              href="/dashboard"
              className="px-5 py-2.5 text-xs font-bold uppercase tracking-wider text-slate-300 hover:text-white transition-colors"
            >
              Dashboard
            </Link>
            <Link
              href="/upload"
              className="px-6 py-2.5 text-xs font-bold uppercase tracking-wider text-slate-950 rounded-xl bg-gradient-to-r from-emerald-400 to-teal-400 hover:from-emerald-300 hover:to-teal-300 shadow-lg shadow-emerald-500/20 transition-all hover:scale-[1.02]"
            >
              Launch Portal
            </Link>
          </div>
        </nav>
      </header>

      {/* Hero Section */}
      <main className="relative z-10 pt-36">
        <section className="max-w-7xl mx-auto px-6 pt-16 pb-28">
          <motion.div
            className="text-center max-w-4xl mx-auto space-y-8"
            initial="hidden"
            animate="visible"
            variants={{
              visible: { transition: { staggerChildren: 0.12 } },
            }}
          >
            <motion.div
              variants={fadeInUp}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-bold uppercase tracking-wider"
            >
              <Sparkles className="w-4 h-4" />
              <span>Official Legal & Policy AI Portal</span>
            </motion.div>

            <motion.h1
              variants={fadeInUp}
              className="text-4xl sm:text-6xl lg:text-7xl font-extrabold font-heading tracking-tight text-white leading-[1.1]"
            >
              Executive Legal Intelligence &{" "}
              <span className="gradient-text-emerald">Clause Risk RAG Engine</span>
            </motion.h1>

            <motion.p
              variants={fadeInUp}
              className="text-base sm:text-lg text-slate-300 max-w-2xl mx-auto leading-relaxed font-medium"
            >
              Automated RAG-powered clause segmentation, vector similarity benchmarking against legal standards, and plain-English risk quantification using Google Gemini.
            </motion.p>

            <motion.div
              variants={fadeInUp}
              className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4"
            >
              <Link
                href="/upload"
                className="group inline-flex items-center gap-2.5 px-8 py-4 text-xs font-bold uppercase tracking-wider text-slate-950 rounded-xl bg-gradient-to-r from-emerald-400 to-teal-400 hover:from-emerald-300 hover:to-teal-300 shadow-xl shadow-emerald-500/20 transition-all hover:scale-[1.02]"
              >
                Upload Document to Analyze
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </Link>
              <Link
                href="/dashboard"
                className="inline-flex items-center gap-2 px-8 py-4 text-xs font-bold uppercase tracking-wider text-slate-300 rounded-xl bg-slate-900 border border-slate-800 hover:bg-slate-800 transition-all"
              >
                Explore Dashboard
              </Link>
            </motion.div>
          </motion.div>
        </section>

        {/* Feature Grid */}
        <section className="py-24 border-t border-slate-800/80 bg-slate-950/60">
          <div className="max-w-7xl mx-auto px-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {features.map((feature, i) => {
                const Icon = feature.icon;
                return (
                  <div
                    key={i}
                    className="p-7 rounded-3xl bg-slate-900/90 border border-slate-800 hover:border-emerald-500/40 transition-all duration-300 shadow-xl"
                  >
                    <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 mb-6">
                      <Icon className="w-6 h-6" />
                    </div>
                    <h3 className="text-base font-bold font-heading text-slate-100 mb-2">
                      {feature.title}
                    </h3>
                    <p className="text-xs text-slate-400 leading-relaxed">
                      {feature.description}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

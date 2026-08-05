"use client";

/**
 * Landing page — the public-facing entry point.
 */

import Link from "next/link";
import { motion } from "framer-motion";
import {
  Shield,
  FileSearch,
  Zap,
  ArrowRight,
  CheckCircle2,
  Brain,
} from "lucide-react";

const features = [
  {
    icon: FileSearch,
    title: "Smart Clause Extraction",
    description:
      "Automatically detect and segment legal clauses from any document format — PDFs, DOCX, and plain text.",
  },
  {
    icon: Brain,
    title: "RAG-Powered Analysis",
    description:
      "Every clause is compared against a curated knowledge base using Retrieval-Augmented Generation for accurate risk assessment.",
  },
  {
    icon: Shield,
    title: "Risk Scoring & Flagging",
    description:
      "Get a 0-100 risk score for every clause with clear explanations of why it's risky and what protections are missing.",
  },
  {
    icon: Zap,
    title: "Plain English Summaries",
    description:
      "Complex legal language translated into simple, easy-to-understand explanations for every clause.",
  },
];

const fadeInUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0 },
};

export default function LandingPage() {
  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Background gradient orbs */}
      <div className="fixed inset-0 -z-10">
        <div className="absolute top-[-20%] left-[-10%] w-[600px] h-[600px] rounded-full bg-blue-600/8 blur-[120px]" />
        <div className="absolute bottom-[-20%] right-[-10%] w-[500px] h-[500px] rounded-full bg-purple-600/8 blur-[120px]" />
        <div className="absolute top-[40%] right-[20%] w-[300px] h-[300px] rounded-full bg-pink-600/5 blur-[100px]" />
      </div>

      {/* Header */}
      <header className="relative z-10">
        <nav className="max-w-7xl mx-auto px-6 py-5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl gradient-brand flex items-center justify-center">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <span className="text-lg font-bold tracking-tight">
              Legal<span className="text-blue-400">Simplifier</span>
            </span>
          </div>
          <div className="flex items-center gap-4">
            <Link
              href="/login"
              className="px-4 py-2 text-sm font-medium text-[var(--text-secondary)] hover:text-white transition-colors"
            >
              Sign In
            </Link>
            <Link
              href="/register"
              className="px-5 py-2.5 text-sm font-semibold text-white rounded-xl gradient-brand hover:opacity-90 transition-opacity"
            >
              Get Started
            </Link>
          </div>
        </nav>
      </header>

      {/* Hero Section */}
      <main className="relative z-10">
        <section className="max-w-7xl mx-auto px-6 pt-20 pb-32">
          <motion.div
            className="text-center max-w-4xl mx-auto"
            initial="hidden"
            animate="visible"
            variants={{
              visible: { transition: { staggerChildren: 0.15 } },
            }}
          >
            <motion.div
              variants={fadeInUp}
              transition={{ duration: 0.6 }}
              className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full glass text-sm text-blue-300 mb-8"
            >
              <Zap className="w-3.5 h-3.5" />
              <span>Powered by Google Gemini & RAG</span>
            </motion.div>

            <motion.h1
              variants={fadeInUp}
              transition={{ duration: 0.6 }}
              className="text-5xl sm:text-6xl lg:text-7xl font-extrabold leading-tight tracking-tight"
            >
              Understand Legal
              <br />
              Documents in{" "}
              <span className="gradient-text">Seconds</span>
            </motion.h1>

            <motion.p
              variants={fadeInUp}
              transition={{ duration: 0.6 }}
              className="mt-6 text-lg sm:text-xl text-[var(--text-secondary)] max-w-2xl mx-auto leading-relaxed"
            >
              Upload any legal document and get instant, clause-by-clause risk
              analysis with plain-English explanations. Powered by AI that
              compares every clause against standard legal benchmarks.
            </motion.p>

            <motion.div
              variants={fadeInUp}
              transition={{ duration: 0.6 }}
              className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4"
            >
              <Link
                href="/register"
                className="group inline-flex items-center gap-2 px-8 py-3.5 text-base font-semibold text-white rounded-xl gradient-brand hover:opacity-90 transition-opacity glow"
              >
                Start Analyzing
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </Link>
              <Link
                href="/login"
                className="inline-flex items-center gap-2 px-8 py-3.5 text-base font-semibold text-[var(--text-primary)] rounded-xl glass hover:bg-white/5 transition-colors"
              >
                Sign In
              </Link>
            </motion.div>

            {/* Trust indicators */}
            <motion.div
              variants={fadeInUp}
              transition={{ duration: 0.6 }}
              className="mt-12 flex flex-wrap items-center justify-center gap-6 text-sm text-[var(--text-muted)]"
            >
              {[
                "No data stored externally",
                "GDPR compliant",
                "Enterprise-grade security",
              ].map((item) => (
                <div key={item} className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span>{item}</span>
                </div>
              ))}
            </motion.div>
          </motion.div>
        </section>

        {/* Features Section */}
        <section className="max-w-7xl mx-auto px-6 pb-32">
          <motion.div
            className="text-center mb-16"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
          >
            <h2 className="text-3xl sm:text-4xl font-bold">
              How It Works
            </h2>
            <p className="mt-4 text-[var(--text-secondary)] max-w-xl mx-auto">
              Our AI pipeline analyzes every clause in your legal documents
              through a rigorous multi-step process.
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {features.map((feature, index) => {
              const Icon = feature.icon;
              return (
                <motion.div
                  key={feature.title}
                  className="group p-8 rounded-2xl glass hover:bg-white/[0.03] transition-all duration-300 gradient-border"
                  initial={{ opacity: 0, y: 30 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.5, delay: index * 0.1 }}
                >
                  <div className="w-12 h-12 rounded-xl bg-blue-500/10 flex items-center justify-center mb-5 group-hover:bg-blue-500/20 transition-colors">
                    <Icon className="w-6 h-6 text-blue-400" />
                  </div>
                  <h3 className="text-xl font-semibold mb-3">
                    {feature.title}
                  </h3>
                  <p className="text-[var(--text-secondary)] leading-relaxed">
                    {feature.description}
                  </p>
                </motion.div>
              );
            })}
          </div>
        </section>

        {/* CTA Section */}
        <section className="max-w-7xl mx-auto px-6 pb-20">
          <motion.div
            className="text-center p-12 rounded-3xl glass gradient-border"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
          >
            <h2 className="text-3xl font-bold mb-4">
              Ready to Simplify Legal Documents?
            </h2>
            <p className="text-[var(--text-secondary)] mb-8 max-w-lg mx-auto">
              Upload your first document and see the AI analysis in action.
              No credit card required.
            </p>
            <Link
              href="/register"
              className="inline-flex items-center gap-2 px-8 py-3.5 text-base font-semibold text-white rounded-xl gradient-brand hover:opacity-90 transition-opacity glow"
            >
              Get Started Free
              <ArrowRight className="w-4 h-4" />
            </Link>
          </motion.div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-[var(--border-primary)] py-8">
        <div className="max-w-7xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-[var(--text-muted)]">
          <p>© 2026 LegalSimplifier. Built with AI.</p>
          <div className="flex items-center gap-6">
            <Link href="#" className="hover:text-white transition-colors">
              Privacy
            </Link>
            <Link href="#" className="hover:text-white transition-colors">
              Terms
            </Link>
            <Link href="#" className="hover:text-white transition-colors">
              Contact
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}

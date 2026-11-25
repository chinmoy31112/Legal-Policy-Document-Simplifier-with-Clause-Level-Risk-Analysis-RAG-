"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import {
  ArrowRight,
  FileText,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme/theme-toggle";

const fadeInUp = {
  hidden: { opacity: 0, y: 12 },
  visible: { opacity: 1, y: 0 },
};

export default function LandingPage() {
  return (
    <div className="min-h-screen relative overflow-hidden bg-[var(--background)] text-[var(--foreground)] font-sans select-none flex flex-col justify-between">
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
            <Link href="/register">
              <Button size="sm">
                Create Account
              </Button>
            </Link>
          </div>
        </nav>
      </header>

      {/* Hero Section */}
      <main className="relative z-10 pt-28 sm:pt-40 flex-1 flex flex-col justify-center">
        <section className="max-w-4xl mx-auto px-4 sm:px-6 py-16 sm:py-24 text-center">
          <motion.div
            className="space-y-6"
            initial="hidden"
            animate="visible"
            variants={{
              visible: { transition: { staggerChildren: 0.08 } },
            }}
          >
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
              className="flex items-center justify-center pt-4"
            >
              <Link href="/upload" className="w-full sm:w-auto">
                <Button size="lg" className="w-full sm:w-auto px-8">
                  <span>Analyze Your Contract</span>
                  <ArrowRight className="w-4 h-4 ml-1.5" />
                </Button>
              </Link>
            </motion.div>
          </motion.div>
        </section>
      </main>
    </div>
  );
}

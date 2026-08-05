"use client";

/**
 * Settings page.
 */

import { motion } from "framer-motion";
import { Header } from "@/components/layout/header";
import { Settings, Key, Bell, Shield, Palette } from "lucide-react";

const settingSections = [
  {
    icon: Key,
    title: "API Configuration",
    description: "Manage your Google AI API key and model settings.",
    color: "text-blue-400",
    bg: "bg-blue-500/10",
  },
  {
    icon: Bell,
    title: "Notifications",
    description: "Configure analysis completion notifications.",
    color: "text-amber-400",
    bg: "bg-amber-500/10",
  },
  {
    icon: Shield,
    title: "Security",
    description: "Manage password, two-factor authentication, and sessions.",
    color: "text-emerald-400",
    bg: "bg-emerald-500/10",
  },
  {
    icon: Palette,
    title: "Appearance",
    description: "Customize theme, layout, and display preferences.",
    color: "text-purple-400",
    bg: "bg-purple-500/10",
  },
];

export default function SettingsPage() {
  return (
    <>
      <Header title="Settings" subtitle="Configure application preferences" />
      <div className="p-8 max-w-3xl space-y-4">
        {settingSections.map((section, index) => {
          const Icon = section.icon;
          return (
            <motion.div
              key={section.title}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.08, duration: 0.4 }}
              className="flex items-center gap-5 p-5 rounded-2xl bg-[var(--bg-surface)] border border-[var(--border-primary)] hover:bg-[var(--bg-elevated)] transition-all cursor-pointer group"
            >
              <div
                className={`w-12 h-12 rounded-xl ${section.bg} flex items-center justify-center flex-shrink-0`}
              >
                <Icon className={`w-6 h-6 ${section.color}`} />
              </div>
              <div className="flex-1">
                <h3 className="text-sm font-semibold">{section.title}</h3>
                <p className="text-sm text-[var(--text-muted)] mt-0.5">
                  {section.description}
                </p>
              </div>
              <Settings className="w-4 h-4 text-[var(--text-muted)] group-hover:text-white transition-colors" />
            </motion.div>
          );
        })}
      </div>
    </>
  );
}

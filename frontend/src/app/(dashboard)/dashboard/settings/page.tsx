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
    title: "AI Pipeline & API Key Configuration",
    description: "Manage Google Gemini API credentials and clause extraction parameters.",
    color: "text-[#55624d]",
    bg: "bg-[#d9e7cd]/60",
  },
  {
    icon: Bell,
    title: "Notifications & Alerts",
    description: "Configure clause risk completion notifications and digests.",
    color: "text-[#b45309]",
    bg: "bg-[#fef3c7]/60",
  },
  {
    icon: Shield,
    title: "Security & Privacy",
    description: "Manage authentication, data encryption, and local session preferences.",
    color: "text-[#55624d]",
    bg: "bg-[#d9e7cd]/60",
  },
  {
    icon: Palette,
    title: "Sanctuary Aesthetics",
    description: "Tranquil interface preferences and editorial typography scale.",
    color: "text-[#755754]",
    bg: "bg-[#fed7d2]/50",
  },
];

export default function SettingsPage() {
  return (
    <>
      <Header title="Sanctuary Settings" subtitle="Configure system preferences and AI pipeline options" />
      <div className="max-w-3xl space-y-4">
        {settingSections.map((section, index) => {
          const Icon = section.icon;
          return (
            <motion.div
              key={section.title}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.08, duration: 0.4 }}
              className="flex items-center gap-6 p-6 rounded-3xl bg-white shadow-ambient hover:shadow-ambient-lg transition-all duration-400 cursor-pointer group"
            >
              <div
                className={`w-14 h-14 rounded-2xl ${section.bg} flex items-center justify-center flex-shrink-0 shadow-ambient`}
              >
                <Icon className={`w-6 h-6 ${section.color}`} />
              </div>
              <div className="flex-1">
                <h3 className="text-base font-bold font-display text-[#191c18]">{section.title}</h3>
                <p className="text-sm text-[#74796e] mt-1 leading-relaxed">
                  {section.description}
                </p>
              </div>
              <Settings className="w-5 h-5 text-[#74796e] group-hover:text-[#55624d] transition-colors" />
            </motion.div>
          );
        })}
      </div>
    </>
  );
}


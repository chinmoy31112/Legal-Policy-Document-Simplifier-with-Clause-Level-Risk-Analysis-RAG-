import * as React from "react";
import {
  CheckCircle2,
  Info,
  AlertTriangle,
  AlertOctagon,
  Scale,
  ShieldAlert,
} from "lucide-react";
import { RiskCategory } from "@/types/analysis";

export interface RiskChipProps {
  category: RiskCategory | string;
  score?: number;
  label?: string;
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function RiskChip({
  category,
  score,
  label,
  size = "md",
  className = "",
}: RiskChipProps) {
  const norm = String(category || "").toLowerCase().replace(/[\s-]/g, "_");

  let visualConfig = {
    label: label || "Standard",
    icon: CheckCircle2,
    classes:
      "bg-[var(--risk-standard-bg)] text-[var(--risk-standard-text)] border border-[var(--risk-standard-border)]",
    outlined: false,
  };

  switch (norm) {
    case "standard":
    case "low":
      visualConfig = {
        label: label || "Standard",
        icon: CheckCircle2,
        classes:
          "bg-[var(--risk-standard-bg)] text-[var(--risk-standard-text)] border border-[var(--risk-standard-border)]",
        outlined: false,
      };
      break;

    case "slightly_unusual":
    case "unusual":
    case "medium":
      visualConfig = {
        label: label || "Slightly Unusual",
        icon: Info,
        classes:
          "bg-[var(--risk-unusual-bg)] text-[var(--risk-unusual-text)] border border-[var(--risk-unusual-border)]",
        outlined: false,
      };
      break;

    case "one_sided":
      visualConfig = {
        label: label || "One-Sided",
        icon: AlertTriangle,
        classes:
          "bg-[var(--risk-onesided-bg)] text-[var(--risk-onesided-text)] border border-[var(--risk-onesided-border)]",
        outlined: false,
      };
      break;

    case "high_risk":
    case "high":
      visualConfig = {
        label: label || "High Risk",
        icon: AlertOctagon,
        classes:
          "bg-[var(--risk-high-bg)] text-[var(--risk-high-text)] border border-[var(--risk-high-border)]",
        outlined: false,
      };
      break;

    case "potentially_unenforceable":
    case "critical":
    case "may_warrant_legal_review":
    default:
      // Unmapped or high-severity review items: High-risk colors with distinct icon & outlined style
      visualConfig = {
        label:
          label ||
          (norm === "potentially_unenforceable"
            ? "Potentially Unenforceable"
            : norm === "may_warrant_legal_review"
            ? "May Warrant Legal Review"
            : norm.split("_").map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(" ") || "Review Warranted"),
        icon: norm === "potentially_unenforceable" ? Scale : ShieldAlert,
        classes:
          "bg-transparent text-[var(--risk-high-text)] border-2 border-[var(--risk-high-text)] border-dashed",
        outlined: true,
      };
      break;
  }

  const Icon = visualConfig.icon;

  const sizeClasses = {
    sm: "text-[11px] py-0.5 px-2 gap-1.5 font-medium",
    md: "text-xs py-1 px-2.5 gap-1.5 font-medium",
    lg: "text-sm py-1.5 px-3.5 gap-2 font-semibold",
  }[size];

  const iconSizes = {
    sm: "h-3 w-3 shrink-0",
    md: "h-3.5 w-3.5 shrink-0",
    lg: "h-4 w-4 shrink-0",
  }[size];

  return (
    <span
      className={`inline-flex items-center rounded-full transition-colors ${sizeClasses} ${visualConfig.classes} ${className}`}
      data-testid="risk-chip"
      data-category={norm}
    >
      <Icon className={iconSizes} aria-hidden="true" />
      <span>{visualConfig.label}</span>
      {typeof score === "number" && (
        <span
          className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] bg-black/10 dark:bg-white/15 tabular-nums font-mono font-medium"
          aria-label={`Risk score: ${Math.round(score)}`}
        >
          {Math.round(score)}
        </span>
      )}
    </span>
  );
}

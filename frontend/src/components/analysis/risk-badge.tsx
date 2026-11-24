<<<<<<< HEAD
import * as React from "react";
import { RiskChip } from "@/components/ui/risk-chip";
=======
import { cn } from "@/lib/utils";
import { AlertTriangle, ShieldAlert, ShieldCheck, HelpCircle } from "lucide-react";
>>>>>>> b678432af63f3a4eb3d5c8ec4f5040c014cfed60

export function RiskBadge({
  category,
  score,
  className,
}: {
  category: string;
  score?: number;
  className?: string;
}) {
<<<<<<< HEAD
  return <RiskChip category={category} score={score} className={className} />;
=======
  let colorClass = "";
  let icon = null;
  let label = category.replace("_", " ");

  const normalized = (category || "").toLowerCase();

  switch (normalized) {
    case "low":
    case "standard":
      colorClass = "bg-emerald-500/15 text-emerald-400 border-emerald-500/30 shadow-sm shadow-emerald-500/10";
      icon = <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />;
      label = "LOW RISK";
      break;
    case "medium":
    case "slightly_unusual":
    case "one_sided":
      colorClass = "bg-yellow-500/15 text-yellow-400 border-yellow-500/30 shadow-sm shadow-yellow-500/10";
      icon = <AlertTriangle className="w-3.5 h-3.5 text-yellow-400" />;
      label = "MEDIUM RISK";
      break;
    case "high":
    case "high_risk":
      colorClass = "bg-orange-500/15 text-orange-400 border-orange-500/30 shadow-sm shadow-orange-500/10 animate-pulse";
      icon = <ShieldAlert className="w-3.5 h-3.5 text-orange-400" />;
      label = "HIGH RISK";
      break;
    case "critical":
    case "potentially_unenforceable":
      colorClass = "bg-red-500/15 text-red-400 border-red-500/30 shadow-sm shadow-red-500/10 animate-pulse";
      icon = <ShieldAlert className="w-3.5 h-3.5 text-red-400" />;
      label = "CRITICAL RISK";
      break;
    default:
      colorClass = "bg-slate-800 text-slate-300 border-slate-700";
      icon = <HelpCircle className="w-3.5 h-3.5 text-slate-400" />;
      label = category.toUpperCase() || "UNRATED";
  }

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-3 py-1 rounded-full border text-[11px] font-bold tracking-wide uppercase transition-all duration-300",
        colorClass,
        className
      )}
    >
      {icon}
      <span>{label}</span>
      {score !== undefined && (
        <span className="ml-1 pl-1.5 border-l border-current/30 font-mono text-[10px]">
          {score}/100
        </span>
      )}
    </span>
  );
>>>>>>> b678432af63f3a4eb3d5c8ec4f5040c014cfed60
}

export { RiskChip };

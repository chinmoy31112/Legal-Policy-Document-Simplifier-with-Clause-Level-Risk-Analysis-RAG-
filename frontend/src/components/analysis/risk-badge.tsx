import { cn } from "@/lib/utils";
import { AlertTriangle, Info, ShieldAlert, ShieldCheck, HelpCircle } from "lucide-react";

export function RiskBadge({
  category,
  score,
  className,
}: {
  category: string;
  score?: number;
  className?: string;
}) {
  let colorClass = "";
  let icon = null;
  let label = category.replace("_", " ");

  switch (category.toLowerCase()) {
    case "standard":
      colorClass = "bg-emerald-500/15 text-emerald-400 border-emerald-500/30 shadow-sm shadow-emerald-500/10";
      icon = <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />;
      break;
    case "slightly_unusual":
      colorClass = "bg-yellow-500/15 text-yellow-400 border-yellow-500/30 shadow-sm shadow-yellow-500/10";
      icon = <Info className="w-3.5 h-3.5 text-yellow-400" />;
      break;
    case "one_sided":
      colorClass = "bg-orange-500/15 text-orange-400 border-orange-500/30 shadow-sm shadow-orange-500/10";
      icon = <AlertTriangle className="w-3.5 h-3.5 text-orange-400" />;
      break;
    case "high_risk":
      colorClass = "bg-red-500/15 text-red-400 border-red-500/30 shadow-sm shadow-red-500/10 animate-pulse";
      icon = <ShieldAlert className="w-3.5 h-3.5 text-red-400" />;
      break;
    case "potentially_unenforceable":
      colorClass = "bg-purple-500/15 text-purple-400 border-purple-500/30 shadow-sm shadow-purple-500/10";
      icon = <ShieldAlert className="w-3.5 h-3.5 text-purple-400" />;
      break;
    default:
      colorClass = "bg-slate-800 text-slate-300 border-slate-700";
      icon = <HelpCircle className="w-3.5 h-3.5 text-slate-400" />;
  }

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-3 py-1 rounded-full border text-[11px] font-bold tracking-wide uppercase transition-all duration-300 capitalize",
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
}

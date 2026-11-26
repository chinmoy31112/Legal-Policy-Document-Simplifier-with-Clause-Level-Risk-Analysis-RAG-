import { cn } from "@/lib/utils";
import { CheckCircle2, Clock, AlertTriangle, Loader2, Ban, PauseCircle } from "lucide-react";

interface StatusBadgeProps {
  status: string;
  stage?: string | null;
  analyzedClauses?: number;
  totalClauses?: number;
}

export function StatusBadge({
  status,
  stage,
  analyzedClauses,
  totalClauses,
}: StatusBadgeProps) {
  let badgeStyle = "bg-slate-800 text-slate-300 border-slate-700";
  let icon = <Clock className="w-3.5 h-3.5" />;
  const normalized = (status || "").trim().toLowerCase().replace(/_/g, " ");
  let label = status;

  switch (normalized) {
    case "completed":
      badgeStyle =
        "bg-emerald-500/15 text-emerald-400 border-emerald-500/30 shadow-sm shadow-emerald-500/10";
      icon = <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />;
      label = "Completed";
      break;

    case "waiting for quota":
      badgeStyle =
        "bg-amber-500/15 text-amber-400 border-amber-500/30 shadow-sm shadow-amber-500/10";
      icon = <PauseCircle className="w-3.5 h-3.5 text-amber-400" />;
      label = "Waiting for Quota";
      break;

    case "cancelling":
      badgeStyle =
        "bg-amber-500/15 text-amber-400 border-amber-500/30 shadow-sm shadow-amber-500/10 animate-pulse";
      icon = <Loader2 className="w-3.5 h-3.5 text-amber-400 animate-spin" />;
      label = "Stopping analysis...";
      break;

    case "cancelled":
      badgeStyle = "bg-slate-500/15 text-slate-400 border-slate-500/30";
      icon = <Ban className="w-3.5 h-3.5 text-slate-400" />;
      label = "Cancelled";
      break;

    case "interrupted":
      badgeStyle = "bg-amber-500/15 text-amber-400 border-amber-500/30";
      icon = <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />;
      label = "Interrupted";
      break;

    case "uploaded":
    case "queued":
      badgeStyle =
        "bg-indigo-500/15 text-indigo-400 border-indigo-500/30 shadow-sm shadow-indigo-500/10";
      icon = <Clock className="w-3.5 h-3.5 text-indigo-400" />;
      label = "Queued";
      break;

    case "running":
    case "extracting":
    case "segmenting":
    case "classifying":
    case "embedding":
    case "analyzing":
    case "scoring":
    case "summarizing": {
      badgeStyle =
        "bg-indigo-500/15 text-indigo-400 border-indigo-500/30 shadow-sm shadow-indigo-500/10 animate-pulse";
      icon = <Loader2 className="w-3.5 h-3.5 text-indigo-400 animate-spin" />;
      const activeStage = (stage || normalized).replace(/_/g, " ");
      const capStage = activeStage.charAt(0).toUpperCase() + activeStage.slice(1);
      if (totalClauses && totalClauses > 0 && analyzedClauses !== undefined) {
        label = `${capStage} (${analyzedClauses} of ${totalClauses} clauses)`;
      } else {
        label = capStage;
      }
      break;
    }

    case "failed":
      badgeStyle = "bg-red-500/15 text-red-400 border-red-500/30 shadow-sm shadow-red-500/10";
      icon = <AlertTriangle className="w-3.5 h-3.5 text-red-400" />;
      label = "Failed";
      break;

    default:
      label = status.charAt(0).toUpperCase() + status.slice(1);
      break;
  }

  return (
    <span
      data-testid="status-badge"
      className={cn(
        "inline-flex items-center gap-1.5 px-3 py-1 rounded-full border text-[11px] font-bold tracking-wide uppercase",
        badgeStyle
      )}
    >
      {icon}
      <span>{label}</span>
    </span>
  );
}

import { cn } from "@/lib/utils";
import { CheckCircle2, Clock, AlertTriangle, Loader2 } from "lucide-react";

export function StatusBadge({ status }: { status: string }) {
  let badgeStyle = "bg-slate-800 text-slate-300 border-slate-700";
  let icon = <Clock className="w-3.5 h-3.5" />;
  let label = status;

  switch (status.toLowerCase()) {
    case "completed":
      badgeStyle = "bg-emerald-500/15 text-emerald-400 border-emerald-500/30 shadow-sm shadow-emerald-500/10";
      icon = <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />;
      label = "Completed";
      break;

    case "analyzing":
    case "extracting":
    case "segmenting":
    case "uploaded":
      badgeStyle = "bg-indigo-500/15 text-indigo-400 border-indigo-500/30 shadow-sm shadow-indigo-500/10 animate-pulse";
      icon = <Loader2 className="w-3.5 h-3.5 text-indigo-400 animate-spin" />;
      label = status === "uploaded" ? "Queued" : status.charAt(0).toUpperCase() + status.slice(1);
      break;

    case "failed":
      badgeStyle = "bg-red-500/15 text-red-400 border-red-500/30 shadow-sm shadow-red-500/10";
      icon = <AlertTriangle className="w-3.5 h-3.5 text-red-400" />;
      label = "Analysis Failed";
      break;

    default:
      label = status.charAt(0).toUpperCase() + status.slice(1);
      break;
  }

  return (
    <span
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

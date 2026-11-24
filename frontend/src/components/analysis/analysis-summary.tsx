import { DocumentAnalysis } from "@/types/analysis";
import { ShieldCheck, ShieldAlert, AlertTriangle, Info, Target, BarChart2, FileJson, FileText, Scale } from "lucide-react";
import { cn } from "@/lib/utils";
import { API_BASE_URL } from "@/lib/constants";

export function AnalysisSummary({ analysis, documentId }: { analysis: DocumentAnalysis; documentId?: string }) {
  // Risk level colors
  let riskColor = "text-emerald-400";
  let bgRiskColor = "bg-emerald-500/10 border-emerald-500/30 text-emerald-400";
  let badgeLabel = "LOW OVERALL RISK";

  if (analysis.overall_risk_score >= 75) {
    riskColor = "text-red-400";
    bgRiskColor = "bg-red-500/10 border-red-500/30 text-red-400";
    badgeLabel = "CRITICAL RISK - REVIEW RECOMMENDED";
  } else if (analysis.overall_risk_score >= 50) {
    riskColor = "text-orange-400";
    bgRiskColor = "bg-orange-500/10 border-orange-500/30 text-orange-400";
    badgeLabel = "HIGH RISK IDENTIFIED";
  } else if (analysis.overall_risk_score >= 25) {
    riskColor = "text-yellow-400";
    bgRiskColor = "bg-yellow-500/10 border-yellow-500/30 text-yellow-400";
    badgeLabel = "MEDIUM RISK DETECTED";
  }

  const distribution = typeof analysis.risk_distribution === "string"
    ? JSON.parse(analysis.risk_distribution)
    : analysis.risk_distribution || {};

  // Support canonical keys (LOW, MEDIUM, HIGH, CRITICAL) or legacy keys
  const lowCount = distribution.LOW ?? distribution.low ?? distribution.standard ?? 0;
  const medCount = distribution.MEDIUM ?? distribution.medium ?? (Number(distribution.slightly_unusual || 0) + Number(distribution.one_sided || 0));
  const highCount = distribution.HIGH ?? distribution.high ?? distribution.high_risk ?? 0;
  const critCount = distribution.CRITICAL ?? distribution.critical ?? distribution.potentially_unenforceable ?? 0;
  const totalClauses = lowCount + medCount + highCount + critCount || 1;

  const handleDownload = (format: "json" | "markdown") => {
    const docId = documentId || analysis.document_id;
    if (!docId) return;
    const url = `${API_BASE_URL}/documents/${docId}/export/${format}`;
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    
    fetch(url, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then((res) => res.blob())
      .then((blob) => {
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = downloadUrl;
        a.download = `risk_analysis_export.${format === "json" ? "json" : "md"}`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(downloadUrl);
      })
      .catch((err) => console.error("Export download failed:", err));
  };

  return (
    <div className="space-y-6 select-none">
      {/* Mandatory Statutory Legal Notice Banner */}
      <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs flex items-start gap-3 shadow-lg">
        <Scale className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
        <div className="space-y-0.5 leading-relaxed font-medium">
          <span className="font-bold uppercase tracking-wider text-amber-400">Important Legal Notice: </span>
          <span>
            This system provides automated document simplification and risk analysis for informational purposes only. It does not provide legal advice, nor does it create an attorney-client relationship. You should consult a qualified legal professional before acting upon or executing any legal document.
          </span>
        </div>
      </div>

      {/* Overall Score Card with Export Action Buttons */}
      <div className={cn("p-6 lg:p-7 border rounded-3xl backdrop-blur-xl flex flex-col md:flex-row items-start md:items-center gap-6 shadow-2xl relative overflow-hidden", bgRiskColor)}>
        <div className="flex-shrink-0 flex flex-col items-center justify-center bg-slate-950 border border-slate-800 shadow-xl rounded-2xl w-28 h-28 p-2">
          <span className={cn("text-4xl font-extrabold font-heading tracking-tight", riskColor)}>
            {analysis.overall_risk_score}
          </span>
          <span className="text-[10px] text-slate-400 uppercase tracking-widest font-bold mt-1">
            Risk Index
          </span>
        </div>

        <div className="flex-1 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <span className="px-3 py-1 rounded-full bg-slate-950 border border-slate-800 text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                <Target className="w-3.5 h-3.5 text-emerald-400" /> Executive Summary
              </span>
              <span className={cn("px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border", bgRiskColor)}>
                {badgeLabel}
              </span>
            </div>

            {/* Export Buttons */}
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => handleDownload("json")}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-950 border border-slate-800 hover:border-emerald-500/40 text-slate-300 hover:text-white text-xs font-bold uppercase tracking-wider transition-all shadow-md"
                title="Download Validated JSON Report"
              >
                <FileJson className="w-3.5 h-3.5 text-emerald-400" />
                <span>JSON Export</span>
              </button>
              <button
                type="button"
                onClick={() => handleDownload("markdown")}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-950 border border-slate-800 hover:border-emerald-500/40 text-slate-300 hover:text-white text-xs font-bold uppercase tracking-wider transition-all shadow-md"
                title="Download Markdown Report"
              >
                <FileText className="w-3.5 h-3.5 text-teal-400" />
                <span>Markdown Export</span>
              </button>
            </div>
          </div>
          <p className="text-xs lg:text-sm leading-relaxed text-slate-200 font-medium">
            {analysis.overall_summary}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Key Recommendations */}
        <div className="p-6 rounded-3xl bg-slate-900/90 border border-slate-800 shadow-xl">
          <h3 className="text-sm font-bold font-heading mb-4 flex items-center text-emerald-400 gap-2">
            <ShieldCheck className="w-4 h-4" /> Actionable Recommendations
          </h3>
          <ul className="space-y-3">
            {analysis.recommendations?.map((rec, i) => (
              <li key={i} className="flex items-start text-xs text-slate-300 font-medium leading-relaxed">
                <span className="w-5 h-5 rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 flex items-center justify-center shrink-0 mr-3 text-[10px] font-bold">
                  {i + 1}
                </span>
                <span className="mt-0.5">{rec}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Risk Distribution Breakdown */}
        <div className="p-6 rounded-3xl bg-slate-900/90 border border-slate-800 shadow-xl">
          <h3 className="text-sm font-bold font-heading mb-4 flex items-center text-indigo-400 gap-2">
            <BarChart2 className="w-4 h-4" /> Clause Risk Breakdown
          </h3>
          <div className="space-y-3">
            <DistributionRow
              label="Low Risk (Standard)"
              count={lowCount}
              total={totalClauses}
              barColor="bg-emerald-500"
              icon={<ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />}
            />
            <DistributionRow
              label="Medium Risk (Imbalanced)"
              count={medCount}
              total={totalClauses}
              barColor="bg-yellow-500"
              icon={<Info className="w-3.5 h-3.5 text-yellow-400" />}
            />
            <DistributionRow
              label="High Risk (One-Sided)"
              count={highCount}
              total={totalClauses}
              barColor="bg-orange-500"
              icon={<AlertTriangle className="w-3.5 h-3.5 text-orange-400" />}
            />
            <DistributionRow
              label="Critical Risk (Review Advised)"
              count={critCount}
              total={totalClauses}
              barColor="bg-red-500"
              icon={<ShieldAlert className="w-3.5 h-3.5 text-red-400" />}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

function DistributionRow({
  label,
  count,
  total,
  barColor,
  icon,
}: {
  label: string;
  count: number;
  total: number;
  barColor: string;
  icon: React.ReactNode;
}) {
  if (count === 0) return null;
  const percentage = total > 0 ? Math.round((count / total) * 100) : 0;

  return (
    <div className="flex items-center text-xs">
      <div className="w-44 flex items-center gap-2 font-medium text-slate-300">
        {icon}
        <span className="truncate">{label}</span>
      </div>
      <div className="flex-1 mx-3 h-2 bg-slate-950 rounded-full overflow-hidden border border-slate-800">
        <div className={cn("h-full rounded-full transition-all duration-500", barColor)} style={{ width: `${percentage}%` }} />
      </div>
      <div className="w-10 text-right text-slate-400 font-mono text-[11px]">
        {count}
      </div>
    </div>
  );
}

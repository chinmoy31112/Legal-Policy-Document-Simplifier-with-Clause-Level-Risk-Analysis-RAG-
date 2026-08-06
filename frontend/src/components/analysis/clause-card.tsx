"use client";

import { useState } from "react";
import { ClauseAnalysis } from "@/types/analysis";
import { RiskBadge } from "./risk-badge";
import { ChevronDown, ChevronUp, AlertCircle, FileText, CheckCircle2, Sparkles, HelpCircle } from "lucide-react";
import { cn } from "@/lib/utils";

export function ClauseCard({
  clause,
  isSelected,
  onClick,
}: {
  clause: ClauseAnalysis;
  isSelected: boolean;
  onClick?: () => void;
}) {
  const [expanded, setExpanded] = useState(false);

  const retrievedClauses = typeof clause.retrieved_clauses === "string"
    ? JSON.parse(clause.retrieved_clauses)
    : clause.retrieved_clauses;

  return (
    <div
      className={cn(
        "border rounded-2xl transition-all duration-300 mb-4 overflow-hidden backdrop-blur-xl",
        isSelected
          ? "border-emerald-500 bg-slate-900/90 shadow-lg shadow-emerald-500/10 ring-1 ring-emerald-500/50"
          : "border-slate-800 hover:border-slate-700 bg-slate-900/60 hover:bg-slate-900/90",
        clause.risk_category === "high_risk" || clause.risk_category === "potentially_unenforceable"
          ? "border-red-500/30 bg-red-950/10"
          : ""
      )}
    >
      {/* Header (Always visible) */}
      <div
        className="p-4 lg:p-5 cursor-pointer flex flex-col gap-3"
        onClick={() => {
          setExpanded(!expanded);
          if (onClick && !isSelected) onClick();
        }}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <span className="text-[11px] font-bold text-slate-400 bg-slate-950 px-2.5 py-1 rounded-lg border border-slate-800">
              Clause {clause.clause?.clause_number || (clause.clause?.clause_index !== undefined ? clause.clause.clause_index + 1 : "Details")}
            </span>
            <RiskBadge category={clause.risk_category} score={clause.risk_score} />
          </div>
          <button className="text-slate-400 hover:text-slate-200 transition-colors p-1">
            {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>

        <div>
          <h3 className="text-xs font-bold text-slate-200 mb-1 line-clamp-1 font-heading">
            {clause.clause?.title || "Legal Provision"}
          </h3>
          <p className="text-xs text-slate-300 font-medium leading-relaxed">
            {clause.plain_english_summary}
          </p>
        </div>
      </div>

      {/* Expanded Content */}
      {expanded && (
        <div className="px-4 pb-5 pt-3 border-t border-slate-800 bg-slate-950/50 space-y-5">
          {/* Original Text */}
          {clause.clause?.content && (
            <div className="space-y-1.5">
              <h4 className="text-[10px] font-bold uppercase tracking-widest text-slate-400 flex items-center gap-1.5">
                <FileText className="w-3.5 h-3.5 text-emerald-400" /> Original Contract Text
              </h4>
              <div className="p-3.5 bg-slate-900 border border-slate-800 rounded-xl text-xs text-slate-300 font-serif leading-relaxed">
                {clause.clause.content}
              </div>
            </div>
          )}

          {/* Key Risks */}
          {clause.risk_reasons && clause.risk_reasons.length > 0 && (
            <div className="space-y-1.5">
              <h4 className="text-[10px] font-bold uppercase tracking-widest text-red-400 flex items-center gap-1.5">
                <AlertCircle className="w-3.5 h-3.5" /> Key Identified Risks
              </h4>
              <ul className="space-y-1.5">
                {clause.risk_reasons.map((reason, i) => (
                  <li key={i} className="flex items-start text-xs text-slate-300 font-medium">
                    <span className="text-red-400 mr-2">•</span>
                    <span>{reason}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Missing Protections */}
          {clause.missing_protections && clause.missing_protections.length > 0 && (
            <div className="space-y-1.5">
              <h4 className="text-[10px] font-bold uppercase tracking-widest text-orange-400 flex items-center gap-1.5">
                <HelpCircle className="w-3.5 h-3.5" /> Missing Protections
              </h4>
              <ul className="space-y-1.5">
                {clause.missing_protections.map((missing, i) => (
                  <li key={i} className="flex items-start text-xs text-slate-300 font-medium">
                    <span className="text-orange-400 mr-2">•</span>
                    <span>{missing}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Suggested Fair Rewrite */}
          {clause.suggested_rewrite && (
            <div className="space-y-1.5">
              <h4 className="text-[10px] font-bold uppercase tracking-widest text-emerald-400 flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5" /> Suggested Balanced Rewrite
              </h4>
              <div className="p-3.5 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-xs text-emerald-300 italic font-medium leading-relaxed">
                "{clause.suggested_rewrite}"
              </div>
            </div>
          )}

          {/* RAG Reference Clauses */}
          {retrievedClauses && retrievedClauses.length > 0 && (
            <div className="space-y-2 pt-3 border-t border-slate-800">
              <h4 className="text-[10px] font-bold uppercase tracking-widest text-slate-400 flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-indigo-400" /> RAG Knowledge Base Benchmark Matches
              </h4>
              <div className="space-y-2">
                {retrievedClauses.map((ref: any, i: number) => (
                  <div key={i} className="p-2.5 bg-slate-900 border border-slate-800 rounded-xl text-[11px] text-slate-300 flex justify-between gap-3">
                    <span className="line-clamp-2">{ref.text || ref.content}</span>
                    {ref.similarity && (
                      <span className="font-mono text-[10px] text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-md border border-emerald-500/20 whitespace-nowrap shrink-0 self-start">
                        Match: {(ref.similarity * 100).toFixed(0)}%
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

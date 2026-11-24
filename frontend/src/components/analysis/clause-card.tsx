"use client";

import { useState } from "react";
import { ClauseAnalysis } from "@/types/analysis";
import { RiskBadge } from "./risk-badge";
import {
  ChevronDown,
  ChevronUp,
  AlertCircle,
  FileText,
  Sparkles,
  BookOpen,
  Scale,
} from "lucide-react";
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

  const retrievedClauses =
    typeof clause.retrieved_clauses === "string"
      ? JSON.parse(clause.retrieved_clauses)
      : clause.retrieved_clauses;

  const catStr = String(clause.risk_category).toLowerCase();
  const isHighRisk =
    catStr === "high" ||
    catStr === "high_risk" ||
    catStr === "critical" ||
    catStr === "potentially_unenforceable";

  return (
    <div
      className={cn(
        "border rounded-2xl transition-all duration-200 overflow-hidden backdrop-blur-xl",
        isSelected
          ? "border-emerald-500 bg-slate-900 shadow-xl shadow-emerald-500/10 ring-1 ring-emerald-500/50"
          : isHighRisk
          ? "border-red-500/30 bg-red-950/10 hover:border-red-500/50"
          : "border-slate-800/80 hover:border-slate-700 bg-slate-900/60 hover:bg-slate-900/90"
      )}
    >
      {/* Card Header */}
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
              Clause {clause.clause?.clause_number || (clause.clause?.clause_index !== undefined ? clause.clause.clause_index + 1 : "Item")}
            </span>
            <RiskBadge category={clause.risk_category} score={clause.risk_score} />
          </div>
          <button className="text-slate-400 hover:text-slate-200 transition-colors p-1">
            {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>

        <div>
          <h4 className="text-xs font-bold text-slate-200 mb-1 line-clamp-1 font-heading">
            {clause.clause?.title || "Legal Provision"}
          </h4>
          <p className="text-xs text-slate-300 font-medium leading-relaxed">
            {clause.plain_english_summary}
          </p>
        </div>
      </div>

      {/* Expanded Breakdown */}
      {expanded && (
        <div className="px-4 pb-5 pt-3 border-t border-slate-800 bg-slate-950/70 space-y-4">
          {/* Original Text */}
          {clause.clause?.content && (
            <div className="space-y-1.5">
              <h5 className="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <FileText className="w-3.5 h-3.5 text-emerald-400" /> Original Contract Text
              </h5>
              <div className="p-3 bg-slate-900 border border-slate-800 rounded-xl text-xs text-slate-300 font-serif leading-relaxed whitespace-pre-wrap">
                {clause.clause.content}
              </div>
            </div>
          )}

          {/* Key Risks */}
          {clause.risk_reasons && clause.risk_reasons.length > 0 && (
            <div className="space-y-1.5">
              <h5 className="text-[10px] font-bold uppercase tracking-wider text-red-400 flex items-center gap-1.5">
                <AlertCircle className="w-3.5 h-3.5" /> Key Risk Factors
              </h5>
              <ul className="space-y-1.5">
                {clause.risk_reasons.map((reason, i) => (
                  <li key={i} className="flex items-start text-xs text-slate-300 font-medium">
                    <span className="text-red-400 mr-2 shrink-0">•</span>
                    <span>{reason}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Missing Protections */}
          {clause.missing_protections && clause.missing_protections.length > 0 && (
            <div className="space-y-1.5">
              <h5 className="text-[10px] font-bold uppercase tracking-wider text-amber-400 flex items-center gap-1.5">
                <Scale className="w-3.5 h-3.5" /> Missing Reciprocal Protections
              </h5>
              <ul className="space-y-1">
                {clause.missing_protections.map((prot, i) => (
                  <li key={i} className="flex items-start text-xs text-amber-200/90 font-medium">
                    <span className="text-amber-400 mr-2 shrink-0">•</span>
                    <span>{prot}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Suggested Balanced Rewrite */}
          {clause.suggested_rewrite && (
            <div className="space-y-1.5">
<<<<<<< HEAD
              <h5 className="text-[10px] font-bold uppercase tracking-wider text-teal-400 flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5" /> Suggested Balanced Alternative
              </h5>
              <div className="p-3 bg-teal-950/20 border border-teal-500/25 rounded-xl text-xs text-teal-200/90 leading-relaxed">
                {clause.suggested_rewrite}
=======
              <h4 className="text-[10px] font-bold uppercase tracking-widest text-emerald-400 flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5" /> Suggested Balanced Rewrite
              </h4>
              <div className="p-3.5 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-xs text-emerald-300 italic font-medium leading-relaxed">
                &ldquo;{clause.suggested_rewrite}&rdquo;
>>>>>>> b678432af63f3a4eb3d5c8ec4f5040c014cfed60
              </div>
            </div>
          )}

          {/* Reference Knowledge Base Grounding */}
          {retrievedClauses && retrievedClauses.length > 0 && (
<<<<<<< HEAD
            <div className="space-y-1.5 pt-1">
              <h5 className="text-[10px] font-bold uppercase tracking-wider text-cyan-400 flex items-center gap-1.5">
                <BookOpen className="w-3.5 h-3.5" /> Grounded Benchmark Precedent
              </h5>
              <div className="space-y-1.5">
                {retrievedClauses.map((ref: { id?: string; title?: string; similarity_score?: number }, idx: number) => (
                  <div
                    key={idx}
                    className="p-2.5 rounded-lg bg-slate-900 border border-slate-800 text-[11px] flex items-center justify-between"
                  >
                    <span className="text-slate-300 font-medium">
                      {ref.title || ref.id || "Standard Commercial Clause"}
                    </span>
                    {ref.similarity_score !== undefined && (
                      <span className="text-cyan-400 font-mono text-[10px] px-2 py-0.5 rounded bg-cyan-500/10 border border-cyan-500/20">
                        {(ref.similarity_score * 100).toFixed(0)}% match
=======
            <div className="space-y-2 pt-3 border-t border-slate-800">
              <h4 className="text-[10px] font-bold uppercase tracking-widest text-slate-400 flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-indigo-400" /> RAG Knowledge Base Benchmark Matches
              </h4>
              <div className="space-y-2">
                {retrievedClauses.map((ref: { text?: string; content?: string; similarity?: number }, i: number) => (
                  <div key={i} className="p-2.5 bg-slate-900 border border-slate-800 rounded-xl text-[11px] text-slate-300 flex justify-between gap-3">
                    <span className="line-clamp-2">{ref.text || ref.content}</span>
                    {ref.similarity && (
                      <span className="font-mono text-[10px] text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-md border border-emerald-500/20 whitespace-nowrap shrink-0 self-start">
                        Match: {(ref.similarity * 100).toFixed(0)}%
>>>>>>> b678432af63f3a4eb3d5c8ec4f5040c014cfed60
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

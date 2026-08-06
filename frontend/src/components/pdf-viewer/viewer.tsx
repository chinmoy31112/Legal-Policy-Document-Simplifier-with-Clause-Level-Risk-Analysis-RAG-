"use client";

import { useState } from "react";
import { ClauseAnalysis } from "@/types/analysis";
import { Document } from "@/types/document";
import { Search, ZoomIn, ZoomOut, FileText, Lock, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

export function DocumentViewer({
  document,
  clauses,
  activeClauseId,
  onClauseSelect,
}: {
  document: Document;
  clauses: ClauseAnalysis[];
  activeClauseId: string | null;
  onClauseSelect: (id: string) => void;
}) {
  const [search, setSearch] = useState("");

  const documentText =
    document.raw_text ||
    clauses.map((c) => c.clause?.content || c.plain_english_summary).join("\n\n");

  const renderHighlightedText = () => {
    if (!clauses || clauses.length === 0) {
      return <p className="whitespace-pre-wrap text-slate-300 font-serif leading-relaxed text-xs">{documentText}</p>;
    }

    return (
      <div className="space-y-6">
        {clauses.map((analysis) => {
          const { clause, risk_category } = analysis;

          let highlightClass =
            "border-l-4 pl-4 py-2.5 transition-all cursor-pointer rounded-r-xl ";

          if (activeClauseId === analysis.id) {
            highlightClass +=
              "bg-emerald-500/15 border-emerald-400 shadow-lg shadow-emerald-500/10 ring-1 ring-emerald-500/30 ";
          } else {
            highlightClass += "hover:bg-slate-800/50 border-transparent ";
          }

          if (risk_category === "high_risk" || risk_category === "potentially_unenforceable") {
            if (activeClauseId === analysis.id) {
              highlightClass = highlightClass
                .replace("bg-emerald-500/15", "bg-red-500/15")
                .replace("border-emerald-400", "border-red-500");
            } else {
              highlightClass += "hover:border-red-500/40 ";
            }
          } else if (risk_category === "one_sided") {
            if (activeClauseId === analysis.id) {
              highlightClass = highlightClass
                .replace("bg-emerald-500/15", "bg-orange-500/15")
                .replace("border-emerald-400", "border-orange-500");
            } else {
              highlightClass += "hover:border-orange-500/40 ";
            }
          }

          return (
            <div
              key={analysis.id}
              id={`clause-${analysis.id}`}
              className={highlightClass}
              onClick={() => onClauseSelect(analysis.id)}
            >
              {clause?.title && (
                <h4 className="font-bold text-xs text-slate-200 mb-1.5 font-heading flex items-center gap-1.5">
                  <Sparkles className="w-3 h-3 text-emerald-400" />
                  {clause.title}
                </h4>
              )}
              <p className="font-serif leading-relaxed whitespace-pre-wrap text-xs text-slate-300">
                {clause?.content || analysis.plain_english_summary}
              </p>
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full bg-slate-950/80 border-l border-slate-800 select-none">
      {/* Toolbar */}
      <div className="flex items-center justify-between p-3 border-b border-slate-800 bg-slate-900/90 shrink-0">
        <div className="flex items-center space-x-2 bg-slate-950 rounded-xl px-3 py-1.5 border border-slate-800">
          <Search className="w-3.5 h-3.5 text-slate-400" />
          <input
            type="text"
            placeholder="Search within agreement text..."
            className="bg-transparent border-none text-xs text-slate-200 placeholder:text-slate-500 outline-none w-44 lg:w-56"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-wider text-emerald-400 bg-emerald-500/10 px-3 py-1 rounded-full border border-emerald-500/20">
          <FileText className="w-3 h-3" />
          <span>Extracted Agreement View</span>
        </div>
      </div>

      {/* Document Content View */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {renderHighlightedText()}
      </div>
    </div>
  );
}

"use client";

import { useState } from 'react';
import { ClauseAnalysis } from '@/types/analysis';
import { RiskBadge } from './risk-badge';
import { ChevronDown, ChevronUp, AlertCircle, FileText, CheckCircle2 } from 'lucide-react';
import { cn } from '@/lib/utils';

export function ClauseCard({ clause, isSelected, onClick }: { clause: ClauseAnalysis; isSelected: boolean; onClick?: () => void }) {
  const [expanded, setExpanded] = useState(false);

  // Parse retrieved clauses if it's a string (from JSON field)
  const retrievedClauses = typeof clause.retrieved_clauses === 'string' 
    ? JSON.parse(clause.retrieved_clauses) 
    : clause.retrieved_clauses;

  return (
    <div 
      className={cn(
        "border rounded-xl transition-all duration-200 mb-4 overflow-hidden",
        isSelected 
          ? "border-primary shadow-md ring-1 ring-primary" 
          : "border-border hover:border-primary/50 hover:shadow-sm bg-card",
        clause.risk_category === 'high_risk' || clause.risk_category === 'potentially_unenforceable' 
          ? "bg-red-50/30 dark:bg-red-950/10" 
          : ""
      )}
    >
      {/* Header (Always visible) */}
      <div 
        className="p-4 cursor-pointer flex flex-col gap-3"
        onClick={() => {
          setExpanded(!expanded);
          if (onClick && !isSelected) onClick();
        }}
      >
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-2">
            <span className="text-xs font-semibold text-muted-foreground bg-muted px-2 py-1 rounded-md">
              Clause {clause.clause?.clause_number || (clause.clause?.clause_index !== undefined ? clause.clause.clause_index + 1 : "Details")}
            </span>
            <RiskBadge category={clause.risk_category} score={clause.risk_score} />
          </div>
          <button className="text-muted-foreground hover:text-foreground">
            {expanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
          </button>
        </div>
        
        <div>
          <h3 className="text-sm font-semibold mb-1 line-clamp-1">{clause.clause?.title || "Legal Provision"}</h3>
          <p className="text-sm text-foreground/90 font-medium">
            {clause.plain_english_summary}
          </p>
        </div>
      </div>

      {/* Expanded Content */}
      {expanded && (
        <div className="px-4 pb-4 pt-2 border-t bg-muted/20 space-y-5 animate-in slide-in-from-top-2">
          
          {/* Original Text */}
          {clause.clause?.content && (
            <div className="space-y-1.5">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center">
                <FileText className="w-3 h-3 mr-1" /> Original Text
              </h4>
              <div className="p-3 bg-background border rounded-lg text-sm text-muted-foreground font-serif leading-relaxed">
                {clause.clause.content}
              </div>
            </div>
          )}

          {/* Risk Reasons */}
          {clause.risk_reasons && clause.risk_reasons.length > 0 && (
            <div className="space-y-1.5">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-destructive flex items-center">
                <AlertCircle className="w-3 h-3 mr-1" /> Key Risks
              </h4>
              <ul className="space-y-2">
                {clause.risk_reasons.map((reason, i) => (
                  <li key={i} className="flex items-start text-sm">
                    <span className="text-destructive mr-2 mt-0.5">•</span>
                    <span>{reason}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Missing Protections */}
          {clause.missing_protections && clause.missing_protections.length > 0 && (
            <div className="space-y-1.5">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-orange-500 flex items-center">
                <AlertCircle className="w-3 h-3 mr-1" /> Missing Protections
              </h4>
              <ul className="space-y-2">
                {clause.missing_protections.map((missing, i) => (
                  <li key={i} className="flex items-start text-sm">
                    <span className="text-orange-500 mr-2 mt-0.5">•</span>
                    <span>{missing}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Suggested Rewrite */}
          {clause.suggested_rewrite && (
            <div className="space-y-1.5">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-green-600 flex items-center">
                <CheckCircle2 className="w-3 h-3 mr-1" /> Suggested Fair Rewrite
              </h4>
              <div className="p-3 bg-green-50 dark:bg-green-950/20 border border-green-100 dark:border-green-900 rounded-lg text-sm text-green-900 dark:text-green-300 italic">
                {clause.suggested_rewrite}
              </div>
            </div>
          )}

          {/* Reference Clauses (RAG Context) */}
          {retrievedClauses && retrievedClauses.length > 0 && (
            <div className="space-y-2 pt-2 border-t">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Standard Reference Clauses Found
              </h4>
              <div className="space-y-2">
                {retrievedClauses.map((ref: any, i: number) => (
                  <div key={i} className="p-2 bg-background border rounded-md text-xs text-muted-foreground flex justify-between">
                    <span className="line-clamp-2 pr-2">{ref.text}</span>
                    <span className="font-mono text-[10px] text-primary whitespace-nowrap self-start">
                      Match: {(ref.similarity * 100).toFixed(0)}%
                    </span>
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

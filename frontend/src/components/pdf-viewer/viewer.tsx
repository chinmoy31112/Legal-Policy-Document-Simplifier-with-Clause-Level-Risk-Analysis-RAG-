"use client";

import { useState, useMemo } from 'react';
import { ClauseAnalysis } from '@/types/analysis';
import { Document } from '@/types/document';
import { Search, ZoomIn, ZoomOut, FileText } from 'lucide-react';
import { cn } from '@/lib/utils';

export function DocumentViewer({ 
  document, 
  clauses,
  activeClauseId,
  onClauseSelect
}: { 
  document: Document; 
  clauses: ClauseAnalysis[];
  activeClauseId: string | null;
  onClauseSelect: (id: string) => void;
}) {
  const [zoom, setZoom] = useState(100);
  const [search, setSearch] = useState('');

  // If we don't have raw text, we construct it from clauses
  const documentText = document.raw_text || clauses.map(c => c.clause?.content || c.plain_english_summary).join('\n\n');

  // Simple highlight logic: we wrap the clause text in a span with the risk color
  const renderHighlightedText = () => {
    if (!clauses || clauses.length === 0) {
      return <p className="whitespace-pre-wrap">{documentText}</p>;
    }

    // This is a simplified rendering strategy: we just render the clauses in order
    // In a full production app, this would use pdf.js with canvas overlays
    return (
      <div className="space-y-6">
        {clauses.map((analysis) => {
          const { clause, risk_category } = analysis;
          
          let highlightClass = "border-l-4 pl-4 py-1 transition-colors cursor-pointer ";
          
          if (activeClauseId === analysis.id) {
            highlightClass += "bg-primary/10 border-primary shadow-sm rounded-r-md ";
          } else {
            highlightClass += "hover:bg-muted/50 border-transparent ";
          }

          // Add subtle color hints based on risk
          if (risk_category === 'high_risk' || risk_category === 'potentially_unenforceable') {
            highlightClass += activeClauseId === analysis.id ? "" : "hover:border-red-300";
            if (activeClauseId === analysis.id) highlightClass = highlightClass.replace("bg-primary/10", "bg-red-50 dark:bg-red-950/30").replace("border-primary", "border-red-500");
          } else if (risk_category === 'one_sided') {
            highlightClass += activeClauseId === analysis.id ? "" : "hover:border-orange-300";
            if (activeClauseId === analysis.id) highlightClass = highlightClass.replace("bg-primary/10", "bg-orange-50 dark:bg-orange-950/30").replace("border-primary", "border-orange-500");
          }

          return (
            <div 
              key={analysis.id} 
              id={`clause-${analysis.id}`}
              className={highlightClass}
              onClick={() => onClauseSelect(analysis.id)}
            >
              {clause?.title && (
                <h4 className="font-bold text-sm mb-2">{clause.title}</h4>
              )}
              <p className="font-serif leading-relaxed whitespace-pre-wrap text-[15px]">
                {clause?.content || analysis.plain_english_summary}
              </p>
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full bg-muted/10 border-l">
      {/* Toolbar */}
      <div className="flex items-center justify-between p-2 border-b bg-card shrink-0">
        <div className="flex items-center space-x-2 bg-muted/50 rounded-md px-2 py-1">
          <Search className="w-4 h-4 text-muted-foreground" />
          <input 
            type="text" 
            placeholder="Search document..." 
            className="bg-transparent border-none text-sm outline-none focus:ring-0 w-48"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        
        <div className="flex items-center space-x-1">
          <button 
            className="p-1.5 hover:bg-muted rounded text-muted-foreground"
            onClick={() => setZoom(Math.max(50, zoom - 10))}
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <span className="text-xs font-medium w-12 text-center">{zoom}%</span>
          <button 
            className="p-1.5 hover:bg-muted rounded text-muted-foreground"
            onClick={() => setZoom(Math.min(200, zoom + 10))}
          >
            <ZoomIn className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Document Content */}
      <div className="flex-1 overflow-y-auto p-8 flex justify-center bg-muted/20">
        <div 
          className="bg-background border shadow-sm w-full max-w-3xl p-12 transition-all"
          style={{ 
            fontSize: `${zoom}%`,
            minHeight: '1056px' // Approx 8.5x11 aspect ratio
          }}
        >
          {renderHighlightedText()}
        </div>
      </div>
    </div>
  );
}

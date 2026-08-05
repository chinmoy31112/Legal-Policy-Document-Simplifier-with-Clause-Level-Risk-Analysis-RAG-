"use client";

import { use, useState } from 'react';
import Link from 'next/link';
import { useDocument } from '@/hooks/use-documents';
import { useDocumentSummary, useClauseAnalyses } from '@/hooks/use-analysis';
import { StatusBadge } from '@/components/documents/status-badge';

import { ArrowLeft, Loader2, AlertCircle } from 'lucide-react';
import { AnalysisSummary } from '@/components/analysis/analysis-summary';
import { ClauseCard } from '@/components/analysis/clause-card';
import { DocumentViewer } from '@/components/pdf-viewer/viewer';

export default function AnalysisPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [activeClauseId, setActiveClauseId] = useState<string | null>(null);

  const { data: document, isLoading: docLoading, isError: docError } = useDocument(id);
  const { data: summary, isLoading: summaryLoading } = useDocumentSummary(id);
  const { data: clauses, isLoading: clausesLoading } = useClauseAnalyses(id);

  if (docLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (docError || !document) {
    return (
      <div className="p-8 text-center text-destructive">
        <AlertCircle className="w-8 h-8 mx-auto mb-4" />
        <p>Document not found or error loading document.</p>
        <Link href="/documents" className="text-primary hover:underline mt-4 inline-block">
          Return to Documents
        </Link>
      </div>
    );
  }

  const isProcessing = [
    'uploaded', 
    'extracting', 
    'segmenting', 
    'analyzing'
  ].includes(document.status);

  const handleClauseSelect = (clauseId: string) => {
    setActiveClauseId(clauseId === activeClauseId ? null : clauseId);
    
    // Scroll the document viewer to the clause
    if (clauseId !== activeClauseId) {
      const element = document.getElementById(`clause-${clauseId}`);
      if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-6 shrink-0">
        <div className="flex items-center space-x-4">
          <Link href="/documents" className="p-2 hover:bg-muted rounded-full transition-colors text-muted-foreground">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">{document.original_filename}</h1>
            <div className="flex items-center space-x-3 mt-1">
              <span className="text-sm text-muted-foreground capitalize">{document.document_type.replace('_', ' ')}</span>
              <StatusBadge status={document.status} />
            </div>
          </div>
        </div>
      </div>

      {isProcessing ? (
        <div className="flex-1 flex flex-col items-center justify-center border rounded-xl bg-card shadow-sm p-12 text-center">
          <Loader2 className="w-12 h-12 animate-spin text-primary mb-6" />
          <h2 className="text-xl font-bold mb-2">Analyzing Document</h2>
          <p className="text-muted-foreground max-w-md">
            We are currently extracting text, segmenting clauses, and running our AI risk models against standard reference contracts. This may take a minute.
          </p>
        </div>
      ) : document.status === 'failed' ? (
        <div className="flex-1 flex items-center justify-center border border-destructive/20 rounded-xl bg-destructive/5 p-12 text-center">
          <div className="max-w-md">
            <AlertCircle className="w-12 h-12 text-destructive mx-auto mb-4" />
            <h2 className="text-xl font-bold text-destructive mb-2">Analysis Failed</h2>
            <p className="text-destructive/80 mb-6">
              There was an error processing this document. This usually happens if the PDF is password protected or heavily corrupted.
            </p>
          </div>
        </div>
      ) : (
        <div className="flex-1 flex overflow-hidden border rounded-xl shadow-sm bg-card">
          {/* Left Panel: Clause List & Summary */}
          <div className="w-1/2 flex flex-col border-r bg-muted/10 overflow-hidden">
            <div className="flex-1 overflow-y-auto p-6">
              {summaryLoading ? (
                <div className="space-y-4 animate-pulse">
                  <div className="h-32 bg-muted rounded-xl w-full"></div>
                </div>
              ) : summary ? (
                <div className="mb-8">
                  <AnalysisSummary analysis={summary} />
                </div>
              ) : null}

              <div className="mt-8">
                <h3 className="font-semibold text-lg mb-4 border-b pb-2">Clause-by-Clause Breakdown</h3>
                {clausesLoading ? (
                  <div className="space-y-4 animate-pulse">
                    {[1, 2, 3].map(i => (
                      <div key={i} className="h-24 bg-muted rounded-xl w-full"></div>
                    ))}
                  </div>
                ) : clauses ? (
                  <div className="space-y-4">
                    {clauses.map((clauseAnalysis) => (
                      <div key={clauseAnalysis.id} id={`card-${clauseAnalysis.id}`}>
                        <ClauseCard 
                          clause={clauseAnalysis} 
                          isSelected={activeClauseId === clauseAnalysis.id} 
                          onClick={() => handleClauseSelect(clauseAnalysis.id)}
                        />
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-muted-foreground">No clauses found.</p>
                )}
              </div>
            </div>
          </div>

          {/* Right Panel: Document Viewer */}
          <div className="w-1/2 flex flex-col bg-muted/30 relative">
            {!clausesLoading && clauses && (
              <DocumentViewer 
                document={document} 
                clauses={clauses} 
                activeClauseId={activeClauseId}
                onClauseSelect={handleClauseSelect}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}

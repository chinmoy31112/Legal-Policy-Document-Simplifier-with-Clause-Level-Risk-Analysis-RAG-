/**
 * TypeScript type definitions for analysis results.
 */

export type RiskCategory =
  | "standard"
  | "slightly_unusual"
  | "one_sided"
  | "high_risk"
  | "potentially_unenforceable"
  | "LOW"
  | "MEDIUM"
  | "HIGH"
  | "CRITICAL";

export interface RetrievedClause {
  clause_id: string;
  title: string | null;
  content: string;
  similarity_score: number;
  source_document: string | null;
  document_type: string | null;
  metadata: Record<string, unknown>;
}

export interface ClauseAnalysis {
  id: string;
  clause_id: string;
  document_id: string;
  plain_english_summary: string;
  risk_score: number;
  risk_category: RiskCategory;
  risk_reasons: string[];
  retrieved_clauses: RetrievedClause[];
  missing_protections: string[];
  suggested_rewrite: string | null;
  confidence_score: number;
  potential_legal_concern: string | null;
  clause?: {
    id: string;
    clause_index: number;
    clause_number?: string | null;
    title?: string | null;
    content: string;
  } | null;
}

export interface RiskDistribution {
  standard?: number;
  slightly_unusual?: number;
  one_sided?: number;
  high_risk?: number;
  potentially_unenforceable?: number;
  low?: number;
  medium?: number;
  high?: number;
  critical?: number;
  total_clauses?: number;
  [key: string]: unknown;
}

export interface DocumentAnalysis {
  id: string;
  document_id: string;
  overall_risk_score: number | null;
  overall_summary: string | null;
  top_risky_clauses: Array<Record<string, unknown>>;
  clause_statistics: Record<string, unknown>;
  risk_distribution: RiskDistribution;
  recommendations: string[];
  is_provisional?: boolean;
}

export interface AnalysisStatus {
  document_id: string;
  status: string;
  progress: number;
  current_step: string | null;
  total_clauses: number;
  analyzed_clauses: number;
  message: string | null;
  job_id?: string | null;
  job_status?: string | null;
  stage?: string | null;
}

export const RISK_CATEGORY_LABELS: Record<string, string> = {
  standard: "Standard",
  low: "Standard",
  slightly_unusual: "Slightly Unusual",
  one_sided: "One-Sided",
  medium: "Slightly Unusual",
  high_risk: "High Risk",
  high: "High Risk",
  potentially_unenforceable: "Potentially Unenforceable",
  critical: "Potentially Unenforceable",
};

export const RISK_CATEGORY_COLORS: Record<string, string> = {
  standard: "#22c55e",
  low: "#22c55e",
  slightly_unusual: "#eab308",
  medium: "#eab308",
  one_sided: "#f97316",
  high_risk: "#ef4444",
  high: "#ef4444",
  potentially_unenforceable: "#dc2626",
  critical: "#dc2626",
};

export const RISK_CATEGORY_BG: Record<string, string> = {
  standard: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  slightly_unusual: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
  one_sided: "bg-orange-500/10 text-orange-400 border-orange-500/20",
  high_risk: "bg-red-500/10 text-red-400 border-red-500/20",
  potentially_unenforceable: "bg-red-700/10 text-red-300 border-red-700/20",
};

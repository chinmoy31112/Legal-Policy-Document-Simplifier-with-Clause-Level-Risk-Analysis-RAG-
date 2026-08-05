/**
 * TypeScript type definitions for documents.
 */

export type DocumentType =
  | "terms_and_conditions"
  | "privacy_policy"
  | "rental_agreement"
  | "employment_contract"
  | "service_agreement"
  | "loan_agreement"
  | "eula"
  | "other";

export type DocumentStatus =
  | "uploaded"
  | "extracting"
  | "segmenting"
  | "embedding"
  | "analyzing"
  | "completed"
  | "failed";

export interface Document {
  id: string;
  original_filename: string;
  filename: string;
  file_type: string;
  file_size: number;
  document_type: DocumentType;
  status: DocumentStatus;
  jurisdiction: string | null;
  is_scanned: boolean;
  raw_text: string | null;
  metadata: Record<string, unknown>;
  clause_count?: number;
  overall_risk_score?: number | null;
  created_at: string;
  updated_at: string | null;
}

export interface DocumentListItem {
  id: string;
  original_filename: string;
  document_type: DocumentType;
  status: DocumentStatus;
  file_size: number;
  is_scanned: boolean;
  clause_count: number;
  overall_risk_score: number | null;
  created_at: string;
}

export interface Clause {
  id: string;
  document_id: string;
  clause_index: number;
  clause_number: string | null;
  title: string | null;
  content: string;
  category: string | null;
  start_page: number | null;
  end_page: number | null;
  start_char: number | null;
  end_char: number | null;
  metadata: Record<string, unknown>;
}

export const DOCUMENT_TYPE_LABELS: Record<DocumentType, string> = {
  terms_and_conditions: "Terms & Conditions",
  privacy_policy: "Privacy Policy",
  rental_agreement: "Rental Agreement",
  employment_contract: "Employment Contract",
  service_agreement: "Service Agreement",
  loan_agreement: "Loan Agreement",
  eula: "EULA",
  other: "Other",
};

export const STATUS_LABELS: Record<DocumentStatus, string> = {
  uploaded: "Uploaded",
  extracting: "Extracting Text",
  segmenting: "Segmenting Clauses",
  embedding: "Generating Embeddings",
  analyzing: "Analyzing",
  completed: "Completed",
  failed: "Failed",
};

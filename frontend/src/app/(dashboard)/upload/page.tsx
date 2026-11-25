"use client";

import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { useRouter } from "next/navigation";
import {
  UploadCloud,
  File as FileIcon,
  FileText,
  X,
  Loader2,
  AlertCircle,
  ShieldCheck,
  ArrowRight,
} from "lucide-react";
import { useUploadDocument } from "@/hooks/use-documents";
import { Button } from "@/components/ui/button";

export default function UploadPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [docType, setDocType] = useState<string>("terms_and_conditions");
  const [jurisdiction, setJurisdiction] = useState<string>("GLOBAL");

  const uploadMutation = useUploadDocument();

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      setFile(acceptedFiles[0]);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
      "text/plain": [".txt"],
    },
    maxFiles: 1,
    maxSize: 50 * 1024 * 1024, // 50MB
  });

  const handleUpload = () => {
    if (!file) return;

    uploadMutation.mutate(
      { file, documentType: docType, jurisdiction },
      {
        onSuccess: (data) => {
          if (data?.id) {
            router.push(`/analysis/${data.id}`);
          }
        },
      }
    );
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto select-none">
      {/* Page Header */}
      <div>
        <h1 className="font-serif text-2xl font-semibold text-[var(--foreground)] tracking-tight">
          Upload Contract or Policy
        </h1>
        <p className="text-xs text-[var(--muted-foreground)] mt-1">
          Initiate structural clause segmentation, vector similarity retrieval, and objective risk scoring
        </p>
      </div>

      {/* Upload Card Container */}
      <div className="p-6 sm:p-8 rounded-[18px] bg-[var(--card)] border border-[var(--border)] shadow-none space-y-6">
        {/* Document Classification Selectors */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div className="space-y-1.5">
            <label
              htmlFor="doc-type-select"
              className="text-xs font-semibold text-[var(--foreground)] flex items-center gap-1.5"
            >
              <FileText className="w-3.5 h-3.5 text-[var(--accent)]" />
              <span>Document Category</span>
            </label>
            <select
              id="doc-type-select"
              className="flex h-10 w-full rounded-[10px] bg-[var(--card)] border border-[var(--border)] px-3 text-xs text-[var(--foreground)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] transition-colors"
              value={docType}
              onChange={(e) => setDocType(e.target.value)}
            >
              <option value="terms_and_conditions">Terms of Service / Terms of Use</option>
              <option value="privacy_policy">Privacy Policy & Data Processing</option>
              <option value="employment_contract">Employment Agreement</option>
              <option value="rental_agreement">Commercial Lease / Rental</option>
              <option value="loan_agreement">Loan & Financial Agreement</option>
              <option value="eula">End User License Agreement (EULA)</option>
              <option value="nda">Non-Disclosure Agreement (NDA)</option>
              <option value="other">General Commercial Agreement</option>
            </select>
          </div>

          <div className="space-y-1.5">
            <label
              htmlFor="jurisdiction-select"
              className="text-xs font-semibold text-[var(--foreground)] flex items-center gap-1.5"
            >
              <ShieldCheck className="w-3.5 h-3.5 text-[var(--accent)]" />
              <span>Jurisdiction Baseline</span>
            </label>
            <select
              id="jurisdiction-select"
              className="flex h-10 w-full rounded-[10px] bg-[var(--card)] border border-[var(--border)] px-3 text-xs text-[var(--foreground)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] transition-colors"
              value={jurisdiction}
              onChange={(e) => setJurisdiction(e.target.value)}
            >
              <option value="GLOBAL">International / Multi-Jurisdictional</option>
              <option value="IN">India (Indian Contract Act / DPDP Act / Common Law)</option>
              <option value="US">United States (Federal & State Baseline)</option>
              <option value="EU">European Union (GDPR / Consumer Directives)</option>
              <option value="UK">United Kingdom (UK GDPR / Common Law)</option>
            </select>
          </div>
        </div>

        {/* Drag & Drop Zone */}
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-[18px] p-8 sm:p-10 text-center transition-all cursor-pointer relative overflow-hidden group select-none ${
            isDragActive
              ? "border-[var(--accent)] bg-[var(--soft-surface)] scale-[1.01]"
              : file
              ? "border-[var(--border)] bg-[var(--soft-surface)]/40"
              : "border-[var(--border)] hover:border-[var(--accent)] bg-[var(--soft-surface)]/20 hover:bg-[var(--soft-surface)]/50"
          }`}
          data-testid="upload-dropzone"
        >
          <input {...getInputProps()} aria-label="Drop legal contract file here" />

          <div className="flex flex-col items-center justify-center space-y-3">
            <div
              className={`w-14 h-14 rounded-[14px] flex items-center justify-center transition-transform duration-200 group-hover:scale-105 ${
                file
                  ? "bg-[var(--risk-standard-bg)] text-[var(--risk-standard-text)] border border-[var(--risk-standard-border)]"
                  : "bg-[var(--soft-surface)] border border-[var(--border)] text-[var(--muted-foreground)] group-hover:text-[var(--accent)]"
              }`}
            >
              <UploadCloud className="w-7 h-7" />
            </div>

            {file ? (
              <div className="space-y-1">
                <p className="text-sm font-semibold text-[var(--foreground)] flex items-center justify-center gap-1.5">
                  <FileIcon className="w-4 h-4 text-[var(--accent)]" />
                  <span>{file.name}</span>
                </p>
                <p className="text-xs text-[var(--muted-foreground)]">
                  {(file.size / (1024 * 1024)).toFixed(2)} MB • Ready for clause extraction
                </p>
              </div>
            ) : (
              <div className="space-y-1">
                <p className="text-sm font-semibold text-[var(--foreground)]">
                  {isDragActive
                    ? "Drop the contract here to upload..."
                    : "Drag & drop a contract or click to browse"}
                </p>
                <p className="text-xs text-[var(--muted-foreground)]">
                  Accepts machine-readable PDFs, DOCX, and TXT files up to 50MB
                </p>
              </div>
            )}

            <div className="flex items-center gap-1.5 pt-1 text-[11px] font-medium text-[var(--muted-foreground)]">
              <span className="px-2 py-0.5 rounded-[6px] bg-[var(--card)] border border-[var(--border)]">PDF</span>
              <span className="px-2 py-0.5 rounded-[6px] bg-[var(--card)] border border-[var(--border)]">DOCX</span>
              <span className="px-2 py-0.5 rounded-[6px] bg-[var(--card)] border border-[var(--border)]">TXT</span>
            </div>
          </div>
        </div>

        {/* Selected File Chip */}
        {file && (
          <div className="flex items-center justify-between p-3.5 rounded-[12px] bg-[var(--soft-surface)] border border-[var(--border)]">
            <div className="flex items-center space-x-3 truncate">
              <div className="w-8 h-8 rounded-[8px] bg-[var(--card)] border border-[var(--border)] flex items-center justify-center text-[var(--accent)] shrink-0">
                <FileIcon className="w-4 h-4" />
              </div>
              <div className="truncate">
                <div className="text-xs font-semibold text-[var(--foreground)] truncate">{file.name}</div>
                <div className="text-[10px] text-[var(--muted-foreground)]">
                  {(file.size / 1024).toFixed(0)} KB • Validated format
                </div>
              </div>
            </div>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setFile(null);
              }}
              aria-label="Remove selected file"
              className="p-1 text-[var(--muted-foreground)] hover:text-[var(--risk-high-text)] rounded-[6px] hover:bg-[var(--card)] transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--accent)]"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Error Message */}
        {uploadMutation.isError && (
          <div
            role="alert"
            className="p-3.5 rounded-[12px] bg-[var(--risk-high-bg)] border border-[var(--risk-high-border)] text-[var(--risk-high-text)] text-xs flex items-center gap-2"
          >
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>
              {uploadMutation.error instanceof Error
                ? uploadMutation.error.message
                : "Upload failed. Please ensure the document is a readable, text-based PDF."}
            </span>
          </div>
        )}

        {/* Action Button */}
        <div className="flex justify-end pt-2">
          <Button
            size="lg"
            onClick={handleUpload}
            disabled={!file || uploadMutation.isPending}
            className="w-full sm:w-auto"
            data-testid="upload-submit-btn"
          >
            {uploadMutation.isPending ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin mr-1" />
                <span>Processing Clauses & Embeddings...</span>
              </>
            ) : (
              <>
                <span>Begin Clause Risk Analysis</span>
                <ArrowRight className="w-4 h-4 ml-1" />
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}

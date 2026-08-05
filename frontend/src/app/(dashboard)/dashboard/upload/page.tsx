"use client";

/**
 * Document upload page with drag-and-drop zone.
 */

import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { motion, AnimatePresence } from "framer-motion";
import { Header } from "@/components/layout/header";
import {
  Upload,
  FileText,
  X,
  Loader2,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";
import { cn, formatFileSize } from "@/lib/utils";
import { ACCEPTED_FILE_TYPES, MAX_FILE_SIZE } from "@/lib/constants";
import type { DocumentType } from "@/types/document";
import { DOCUMENT_TYPE_LABELS } from "@/types/document";
import { useUploadDocument } from "@/hooks/use-documents";
import { useRouter } from "next/navigation";

const documentTypes: { value: DocumentType; label: string }[] = Object.entries(
  DOCUMENT_TYPE_LABELS
).map(([value, label]) => ({ value: value as DocumentType, label }));

export default function UploadPage() {
  const router = useRouter();
  const uploadMutation = useUploadDocument();
  const [files, setFiles] = useState<File[]>([]);
  const [documentType, setDocumentType] = useState<DocumentType>("other");
  const [jurisdiction, setJurisdiction] = useState("");

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setFiles(acceptedFiles);
  }, []);

  const { getRootProps, getInputProps, isDragActive, isDragReject } =
    useDropzone({
      onDrop,
      accept: ACCEPTED_FILE_TYPES,
      maxSize: MAX_FILE_SIZE,
      maxFiles: 1,
      multiple: false,
    });

  const handleUpload = async () => {
    if (files.length === 0) return;
    uploadMutation.mutate(
      { file: files[0], documentType, jurisdiction },
      {
        onSuccess: (data) => {
          router.push(`/analysis/${data.id}`);
        },
      }
    );
  };

  const removeFile = () => {
    setFiles([]);
  };

  return (
    <>
      <Header
        title="Upload Document"
        subtitle="Upload a legal document for AI-powered analysis"
      />
      <div className="p-8 max-w-3xl mx-auto space-y-8">
        {/* Dropzone */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div
            {...getRootProps()}
            className={cn(
              "relative p-12 rounded-2xl border-2 border-dashed cursor-pointer",
              "transition-all duration-300",
              isDragActive && !isDragReject
                ? "border-blue-400 bg-blue-500/5"
                : isDragReject
                  ? "border-red-400 bg-red-500/5"
                  : "border-[var(--border-primary)] hover:border-blue-400/50 hover:bg-blue-500/[0.02]"
            )}
          >
            <input {...getInputProps()} />
            <div className="flex flex-col items-center text-center">
              <div
                className={cn(
                  "w-16 h-16 rounded-2xl flex items-center justify-center mb-5 transition-colors",
                  isDragActive ? "bg-blue-500/20" : "bg-blue-500/10"
                )}
              >
                <Upload
                  className={cn(
                    "w-8 h-8 transition-colors",
                    isDragActive ? "text-blue-300" : "text-blue-400"
                  )}
                />
              </div>
              <h3 className="text-lg font-semibold mb-2">
                {isDragActive
                  ? "Drop your document here"
                  : "Drag & drop your legal document"}
              </h3>
              <p className="text-sm text-[var(--text-muted)] mb-4">
                or click to browse your files
              </p>
              <p className="text-xs text-[var(--text-muted)]">
                Supports PDF, DOCX, TXT • Max 50 MB
              </p>
            </div>
          </div>
        </motion.div>

        {/* Selected file */}
        <AnimatePresence>
          {files.length > 0 && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="rounded-2xl bg-[var(--bg-surface)] border border-[var(--border-primary)] p-5"
            >
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-blue-500/10 flex items-center justify-center flex-shrink-0">
                  <FileText className="w-6 h-6 text-blue-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">
                    {files[0].name}
                  </p>
                  <p className="text-xs text-[var(--text-muted)]">
                    {formatFileSize(files[0].size)}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={(e) => { e.preventDefault(); removeFile(); }}
                  className="p-2 rounded-lg hover:bg-white/5 transition-colors"
                >
                  <X className="w-4 h-4 text-[var(--text-muted)]" />
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Configuration */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.5 }}
          className="rounded-2xl bg-[var(--bg-surface)] border border-[var(--border-primary)] p-6 space-y-5"
        >
          <h3 className="text-base font-semibold">Document Details</h3>

          {/* Document type */}
          <div>
            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-2">
              Document Type
            </label>
            <select
              value={documentType}
              onChange={(e) =>
                setDocumentType(e.target.value as DocumentType)
              }
              className="w-full px-4 py-2.5 rounded-xl bg-[var(--bg-primary)] border border-[var(--border-primary)] text-sm text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500/50 transition-all"
            >
              {documentTypes.map((dt) => (
                <option key={dt.value} value={dt.value}>
                  {dt.label}
                </option>
              ))}
            </select>
          </div>

          {/* Jurisdiction */}
          <div>
            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-2">
              Jurisdiction (optional)
            </label>
            <input
              type="text"
              placeholder="e.g., US, EU, UK, India"
              value={jurisdiction}
              onChange={(e) => setJurisdiction(e.target.value)}
              className="w-full px-4 py-2.5 rounded-xl bg-[var(--bg-primary)] border border-[var(--border-primary)] text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500/50 transition-all"
            />
          </div>
        </motion.div>

        {/* Upload button */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.5 }}
        >
          {uploadMutation.isError && (
            <div className="mb-4 p-4 bg-red-500/10 text-red-500 text-sm rounded-xl flex items-start border border-red-500/20">
              <AlertCircle className="w-5 h-5 mr-2 shrink-0 mt-0.5" />
              <span>
                {uploadMutation.error instanceof Error
                  ? uploadMutation.error.message
                  : "An error occurred during upload. Please try again."}
              </span>
            </div>
          )}

          <button
            type="button"
            onClick={(e) => { e.preventDefault(); handleUpload(); }}
            disabled={files.length === 0 || uploadMutation.isPending}
            className={cn(
              "w-full py-3.5 rounded-xl text-base font-semibold",
              "transition-all duration-200",
              files.length > 0 && !uploadMutation.isPending
                ? "gradient-brand text-white hover:opacity-90 glow cursor-pointer"
                : "bg-[var(--bg-elevated)] text-[var(--text-muted)] cursor-not-allowed"
            )}
          >
            {uploadMutation.isPending ? (
              <span className="flex items-center justify-center gap-2">
                <Loader2 className="w-5 h-5 animate-spin" />
                Uploading & Processing...
              </span>
            ) : (
              "Upload & Analyze"
            )}
          </button>
        </motion.div>
      </div>
    </>
  );
}

"use client";

import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { useRouter } from "next/navigation";
import { Header } from "@/components/layout/header";
import {
  UploadCloud,
  File as FileIcon,
  X,
  Loader2,
  AlertCircle,
  ShieldCheck,
  Zap,
  Sparkles,
  ArrowRight
} from "lucide-react";
import { useUploadDocument } from "@/hooks/use-documents";

export default function UploadPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [docType, setDocType] = useState<string>("terms_and_conditions");
  const [jurisdiction, setJurisdiction] = useState<string>("US");

  const uploadMutation = useUploadDocument();

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      setFile(acceptedFiles[0]);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
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
    <>
      <Header
        title="Upload Legal Agreement or Policy"
        subtitle="Initiate automated AI clause segmentation, RAG benchmarking, and risk quantification"
      />
      <div className="mx-auto max-w-4xl space-y-8">
        <div className="p-8 lg:p-10 rounded-3xl bg-slate-900/90 border border-slate-800 shadow-2xl space-y-8 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-80 h-80 bg-emerald-500/10 blur-[100px] rounded-full pointer-events-none" />

          <div className="space-y-6 relative z-10">
            {/* Configuration Selectors */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                  <Zap className="w-3.5 h-3.5 text-emerald-400" /> Document Category
                </label>
                <select
                  className="flex h-12 w-full rounded-xl bg-slate-950 border border-slate-800 px-4 py-2 text-xs text-slate-100 focus:border-emerald-500 focus:outline-none transition-all"
                  value={docType}
                  onChange={(e) => setDocType(e.target.value)}
                >
                  <option value="terms_and_conditions">Terms of Service / Agreement</option>
                  <option value="privacy_policy">Privacy Policy & Data Terms</option>
                  <option value="employment_contract">Employment Contract</option>
                  <option value="rental_agreement">Rental / Lease Agreement</option>
                  <option value="loan_agreement">Loan & Financial Agreement</option>
                  <option value="eula">End User License Agreement (EULA)</option>
                  <option value="other">Other General Contract</option>
                </select>
              </div>

              <div className="space-y-2">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" /> Governing Jurisdiction
                </label>
                <select
                  className="flex h-12 w-full rounded-xl bg-slate-950 border border-slate-800 px-4 py-2 text-xs text-slate-100 focus:border-emerald-500 focus:outline-none transition-all"
                  value={jurisdiction}
                  onChange={(e) => setJurisdiction(e.target.value)}
                >
                  <option value="US">United States (Federal Standard)</option>
                  <option value="US-CA">California, US (CCPA Standard)</option>
                  <option value="US-NY">New York, US</option>
                  <option value="UK">United Kingdom (UK GDPR)</option>
                  <option value="EU">European Union (GDPR Standard)</option>
                  <option value="IN">India (DPDP Standard)</option>
                  <option value="AU">Australia</option>
                  <option value="OTHER">International / General</option>
                </select>
              </div>
            </div>

            {/* Drag & Drop Zone */}
            <div className="space-y-2">
              <label className="text-xs font-bold uppercase tracking-wider text-slate-300">
                Document File (PDF, DOCX, TXT)
              </label>

              {!file ? (
                <div
                  {...getRootProps()}
                  className={`
                    border-2 border-dashed rounded-3xl p-10 text-center cursor-pointer transition-all duration-300 bg-slate-950/60
                    ${
                      isDragActive
                        ? "border-emerald-400 bg-emerald-500/10 shadow-lg shadow-emerald-500/10"
                        : "border-slate-800 hover:border-emerald-500/50 hover:bg-slate-900/90"
                    }
                    ${isDragReject ? "border-red-500 bg-red-500/10" : ""}
                  `}
                >
                  <input {...getInputProps()} />
                  <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 mb-4 shadow-lg shadow-emerald-500/10">
                    <UploadCloud className="h-8 w-8" />
                  </div>
                  <h3 className="text-base font-bold font-heading text-slate-100">
                    {isDragActive
                      ? "Release to upload agreement..."
                      : "Drag & drop document here, or click to browse"}
                  </h3>
                  <p className="text-xs text-slate-400 mt-2 font-medium">
                    Supports PDF (with PyMuPDF OCR fallback), DOCX, and TXT (Up to 50MB)
                  </p>
                </div>
              ) : (
                <div className="flex items-center justify-between p-5 rounded-2xl bg-slate-950 border border-emerald-500/30 shadow-lg shadow-emerald-500/5">
                  <div className="flex items-center space-x-4">
                    <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                      <FileIcon className="h-6 w-6" />
                    </div>
                    <div>
                      <p className="text-sm font-bold font-heading text-slate-100">{file.name}</p>
                      <p className="text-xs text-slate-400">
                        {(file.size / 1024 / 1024).toFixed(2)} MB • Ready for Analysis
                      </p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.preventDefault();
                      setFile(null);
                    }}
                    className="p-2 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded-xl transition-all"
                    disabled={uploadMutation.isPending}
                  >
                    <X className="h-5 w-5" />
                  </button>
                </div>
              )}
            </div>

            {uploadMutation.isError && (
              <div className="p-4 bg-red-500/10 border border-red-500/30 text-red-400 text-xs rounded-xl flex items-start font-medium shadow-md">
                <AlertCircle className="h-4 w-4 mr-2.5 shrink-0 mt-0.5" />
                <span>
                  {uploadMutation.error instanceof Error
                    ? uploadMutation.error.message
                    : "An error occurred during document upload. Please try again."}
                </span>
              </div>
            )}
          </div>

          <div className="flex items-center justify-between pt-6 border-t border-slate-800 relative z-10">
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <Sparkles className="w-4 h-4 text-emerald-400" />
              <span>Automated Gemini 3.5 RAG Analysis</span>
            </div>

            <button
              type="button"
              onClick={(e) => {
                e.preventDefault();
                handleUpload();
              }}
              disabled={!file || uploadMutation.isPending}
              className="inline-flex items-center justify-center gap-2 rounded-xl text-xs font-bold uppercase tracking-wider bg-gradient-to-r from-emerald-400 to-teal-400 text-slate-950 hover:from-emerald-300 hover:to-teal-300 h-12 px-8 shadow-lg shadow-emerald-500/20 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed hover:scale-[1.02]"
            >
              {uploadMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin text-slate-950" />
                  Initializing Pipeline...
                </>
              ) : (
                <>
                  Launch AI Analysis <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

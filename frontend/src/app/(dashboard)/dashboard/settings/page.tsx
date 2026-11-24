"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Header } from "@/components/layout/header";
import { useAuth } from "@/providers/auth-provider";
import { apiClient } from "@/lib/api-client";
import {
  User,
  Shield,
  Cpu,
  Trash2,
  AlertTriangle,
  Loader2,
  CheckCircle2,
  LogOut,
  Scale,
  Sparkles,
} from "lucide-react";

export default function SettingsPage() {
  const router = useRouter();
  const { user, logout } = useAuth();
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [confirmText, setConfirmText] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState("");

  const handleDeleteAccount = async () => {
    if (confirmText !== "DELETE") {
      setDeleteError('Please type "DELETE" to confirm account erasure.');
      return;
    }

    setIsDeleting(true);
    setDeleteError("");

    try {
      await apiClient.delete("/auth/me");
      logout();
      router.push("/login");
    } catch (err: unknown) {
      const errorMsg =
        err instanceof Error ? err.message : "Failed to delete account. Please try again.";
      setDeleteError(errorMsg);
      setIsDeleting(false);
    }
  };

  return (
    <>
      <Header
        title="Settings & Privacy Compliance"
        subtitle="Manage user credentials, AI models, and GDPR data retention rights"
      />

      <div className="mx-auto max-w-4xl space-y-8 select-none">
        {/* User Profile Card */}
        <div className="p-8 rounded-3xl bg-slate-900/90 border border-slate-800 shadow-xl space-y-6">
          <div className="flex items-center justify-between border-b border-slate-800 pb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                <User className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold font-heading text-slate-100">
                  Officer Identity & Session
                </h3>
                <p className="text-xs text-slate-400">
                  Authenticated credentials and tenant identity
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={logout}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold uppercase tracking-wider text-slate-300 bg-slate-950 border border-slate-800 hover:border-slate-700 hover:text-white transition-all shadow-md"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span>Sign Out</span>
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800">
              <span className="text-slate-500 font-bold uppercase text-[10px] tracking-wider block mb-1">
                Full Name
              </span>
              <span className="text-slate-200 font-semibold text-sm">
                {user?.full_name || "Legal Review Officer"}
              </span>
            </div>

            <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800">
              <span className="text-slate-500 font-bold uppercase text-[10px] tracking-wider block mb-1">
                Email Address
              </span>
              <span className="text-slate-200 font-semibold text-sm">
                {user?.email || "officer@example.com"}
              </span>
            </div>

            <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800">
              <span className="text-slate-500 font-bold uppercase text-[10px] tracking-wider block mb-1">
                Account Status
              </span>
              <span className="inline-flex items-center gap-1.5 text-emerald-400 font-semibold">
                <CheckCircle2 className="w-3.5 h-3.5" /> Active & Verified Tenant
              </span>
            </div>

            <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800">
              <span className="text-slate-500 font-bold uppercase text-[10px] tracking-wider block mb-1">
                Per-User Isolation
              </span>
              <span className="inline-flex items-center gap-1.5 text-emerald-400 font-semibold">
                <Shield className="w-3.5 h-3.5" /> Strict Tenant Data Boundary Active
              </span>
            </div>
          </div>
        </div>

        {/* AI Engine & System Specifications */}
        <div className="p-8 rounded-3xl bg-slate-900/90 border border-slate-800 shadow-xl space-y-6">
          <div className="flex items-center gap-3 border-b border-slate-800 pb-4">
            <div className="w-10 h-10 rounded-xl bg-indigo-500/15 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold font-heading text-slate-100">
                AI Architecture & Verified Models
              </h3>
              <p className="text-xs text-slate-400">
                Official Google Gen AI SDK models & vector configurations
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
            <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 space-y-1">
              <span className="text-slate-500 font-bold uppercase text-[10px] tracking-wider block">
                Reasoning LLM
              </span>
              <div className="text-slate-200 font-bold font-mono">gemini-2.5-flash</div>
              <p className="text-[11px] text-slate-400">
                Structured JSON schema validation with up to 2 repair retries
              </p>
            </div>

            <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 space-y-1">
              <span className="text-slate-500 font-bold uppercase text-[10px] tracking-wider block">
                Embedding Model
              </span>
              <div className="text-slate-200 font-bold font-mono">gemini-embedding-2</div>
              <p className="text-[11px] text-slate-400">
                768-dimensional legal clause vector representations
              </p>
            </div>

            <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 space-y-1">
              <span className="text-slate-500 font-bold uppercase text-[10px] tracking-wider block">
                Vector Knowledge Base
              </span>
              <div className="text-emerald-400 font-bold font-mono flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5" /> Curated Reference KB
              </div>
              <p className="text-[11px] text-slate-400">
                232 verified standard benchmark clauses (Top-K semantic retrieval)
              </p>
            </div>
          </div>
        </div>

        {/* GDPR Right to Erasure / Delete-My-Data */}
        <div className="p-8 rounded-3xl bg-red-950/20 border border-red-500/30 shadow-xl space-y-6">
          <div className="flex items-center gap-3 border-b border-red-500/20 pb-4">
            <div className="w-10 h-10 rounded-xl bg-red-500/15 border border-red-500/30 flex items-center justify-center text-red-400">
              <Scale className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold font-heading text-red-200">
                Privacy & GDPR Right to Erasure (Delete-My-Data)
              </h3>
              <p className="text-xs text-red-400/80">
                Permanent deletion of account, documents, segmented clauses, and disk artifacts
              </p>
            </div>
          </div>

          <p className="text-xs text-slate-300 leading-relaxed font-medium">
            Under GDPR Article 17 and global privacy standards, you have the right to request the
            immediate and irreversible erasure of all personal data. Clicking the button below will
            permanently delete your user account, all uploaded legal documents, extracted text,
            vector embeddings, analysis records, and physical files from server storage.
          </p>

          <div>
            <button
              type="button"
              onClick={() => setShowDeleteModal(true)}
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl text-xs font-bold uppercase tracking-wider text-white bg-red-600 hover:bg-red-500 transition-all shadow-lg shadow-red-600/20 hover:scale-[1.02]"
            >
              <Trash2 className="w-4 h-4" />
              <span>Permanently Delete My Account & All Documents</span>
            </button>
          </div>
        </div>
      </div>

      {/* Confirmation Modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-3xl bg-slate-900 border border-red-500/40 p-7 shadow-2xl space-y-5 animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-center gap-3 text-red-400">
              <div className="w-10 h-10 rounded-2xl bg-red-500/15 border border-red-500/30 flex items-center justify-center">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <h3 className="text-base font-bold font-heading text-slate-100">
                Confirm Irreversible Account Deletion
              </h3>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">
              This action <strong className="text-red-400">CANNOT be undone</strong>. All documents,
              analyses, clauses, and account records will be permanently purged.
            </p>

            <div className="space-y-2">
              <label className="text-[11px] font-bold uppercase tracking-wider text-slate-400 block">
                Type <span className="text-red-400 font-mono">DELETE</span> below to confirm:
              </label>
              <input
                type="text"
                value={confirmText}
                onChange={(e) => setConfirmText(e.target.value)}
                placeholder="DELETE"
                className="w-full px-4 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-100 focus:border-red-500 focus:outline-none font-mono"
              />
            </div>

            {deleteError && (
              <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-xs font-medium">
                {deleteError}
              </div>
            )}

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => {
                  setShowDeleteModal(false);
                  setConfirmText("");
                  setDeleteError("");
                }}
                disabled={isDeleting}
                className="px-4 py-2 text-xs font-bold text-slate-400 hover:text-slate-200 transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleDeleteAccount}
                disabled={confirmText !== "DELETE" || isDeleting}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold uppercase tracking-wider text-white bg-red-600 hover:bg-red-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-md shadow-red-600/20"
              >
                {isDeleting ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Purging Data...</span>
                  </>
                ) : (
                  <>
                    <Trash2 className="w-3.5 h-3.5" />
                    <span>Delete Everything</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

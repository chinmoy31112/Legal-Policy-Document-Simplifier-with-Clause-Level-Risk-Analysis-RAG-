"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/providers/auth-provider";
import { apiClient } from "@/lib/api-client";
import { closeAllDocumentStreams } from "@/lib/sse-registry";
import {
  User,
  Shield,
  Trash2,
  AlertTriangle,
  Loader2,
  LogOut,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function SettingsPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
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
      closeAllDocumentStreams();
      await queryClient.cancelQueries();
      queryClient.clear();
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
    <div className="mx-auto max-w-4xl space-y-6 select-none">
      {/* Page Header */}
      <div>
        <h1 className="font-serif text-2xl font-semibold text-[var(--foreground)] tracking-tight">
          Settings & Privacy Compliance
        </h1>
        <p className="text-xs text-[var(--muted-foreground)] mt-1">
          Manage user credentials, model configuration status, and GDPR erasure rights
        </p>
      </div>

      {/* User Profile Card */}
      <div className="p-6 rounded-[18px] bg-[var(--card)] border border-[var(--border)] shadow-none space-y-5">
        <div className="flex items-center justify-between border-b border-[var(--border)] pb-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-[10px] bg-[var(--soft-surface)] border border-[var(--border)] flex items-center justify-center text-[var(--accent)]">
              <User className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-serif text-base font-semibold text-[var(--foreground)]">User Profile</h3>
              <p className="text-xs text-[var(--muted-foreground)]">Authenticated legal reviewer credentials</p>
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={logout}
          >
            <LogOut className="w-3.5 h-3.5 mr-1" />
            <span>Sign Out</span>
          </Button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div className="p-3.5 rounded-[10px] bg-[var(--soft-surface)] border border-[var(--border)] space-y-1">
            <span className="text-[10px] font-semibold text-[var(--muted-foreground)] uppercase tracking-wider">Full Name</span>
            <div className="text-xs font-medium text-[var(--foreground)]">{user?.full_name || "Legal Reviewer"}</div>
          </div>
          <div className="p-3.5 rounded-[10px] bg-[var(--soft-surface)] border border-[var(--border)] space-y-1">
            <span className="text-[10px] font-semibold text-[var(--muted-foreground)] uppercase tracking-wider">Email Address</span>
            <div className="text-xs font-medium text-[var(--foreground)]">{user?.email || "user@contract.ai"}</div>
          </div>
        </div>
      </div>

      {/* GDPR Data Erasure Card */}
      <div className="p-6 rounded-[18px] bg-[var(--risk-high-bg)]/40 border border-[var(--risk-high-border)] shadow-none space-y-5">
        <div className="flex items-center gap-3 border-b border-[var(--risk-high-border)] pb-4">
          <div className="w-9 h-9 rounded-[10px] bg-[var(--risk-high-bg)] border border-[var(--risk-high-border)] flex items-center justify-center text-[var(--risk-high-text)]">
            <Shield className="w-4 h-4" />
          </div>
          <div>
            <h3 className="font-serif text-base font-semibold text-[var(--risk-high-text)]">
              GDPR Compliance & Cascade Data Erasure
            </h3>
            <p className="text-xs text-[var(--risk-high-text)]/80">
              Permanently purge your account, uploaded agreements, and clause analyses
            </p>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1 max-w-lg text-xs text-[var(--foreground)]">
            <p className="font-semibold text-[var(--risk-high-text)]">Right to Erasure (Article 17 GDPR):</p>
            <p className="text-[var(--muted-foreground)] leading-relaxed">
              Purges all user records, documents on disk, extracted clauses, risk analyses, and audit logs immediately. This action cannot be reversed.
            </p>
          </div>

          <Button
            variant="danger"
            size="sm"
            onClick={() => setShowDeleteModal(true)}
            className="shrink-0"
          >
            <Trash2 className="w-3.5 h-3.5 mr-1" />
            <span>Delete Account & Data</span>
          </Button>
        </div>
      </div>

      {/* Confirmation Modal */}
      {showDeleteModal && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Confirm permanent account deletion"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4"
        >
          <div className="w-full max-w-md rounded-[18px] bg-[var(--card)] border border-[var(--border)] p-6 space-y-4 shadow-xl text-[var(--foreground)]">
            <div className="w-12 h-12 rounded-[12px] bg-[var(--risk-high-bg)] border border-[var(--risk-high-border)] flex items-center justify-center text-[var(--risk-high-text)] mx-auto">
              <AlertTriangle className="w-6 h-6" />
            </div>

            <div className="text-center space-y-1">
              <h4 className="font-serif text-lg font-semibold text-[var(--foreground)]">Permanently Delete Account?</h4>
              <p className="text-xs text-[var(--muted-foreground)] leading-relaxed">
                This will delete your credentials and all uploaded contracts from PostgreSQL and disk storage.
              </p>
            </div>

            {deleteError && (
              <div
                role="alert"
                className="p-3 rounded-[10px] bg-[var(--risk-high-bg)] border border-[var(--risk-high-border)] text-[var(--risk-high-text)] text-xs"
              >
                {deleteError}
              </div>
            )}

            <div className="space-y-1.5">
              <label htmlFor="confirm-delete-input" className="text-xs text-[var(--muted-foreground)] font-medium block">
                Type <strong className="text-[var(--risk-high-text)]">DELETE</strong> to confirm:
              </label>
              <Input
                id="confirm-delete-input"
                type="text"
                value={confirmText}
                onChange={(e) => setConfirmText(e.target.value)}
                placeholder="DELETE"
              />
            </div>

            <div className="flex gap-2.5 pt-2">
              <Button
                variant="outline"
                className="flex-1"
                onClick={() => {
                  setShowDeleteModal(false);
                  setConfirmText("");
                  setDeleteError("");
                }}
              >
                Cancel
              </Button>
              <Button
                variant="danger"
                className="flex-1"
                onClick={handleDeleteAccount}
                disabled={isDeleting || confirmText !== "DELETE"}
              >
                {isDeleting ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : <Trash2 className="w-4 h-4 mr-1" />}
                <span>Confirm Purge</span>
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

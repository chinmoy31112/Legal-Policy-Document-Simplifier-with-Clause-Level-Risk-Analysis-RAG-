import * as React from "react";
import { AlertCircle } from "lucide-react";

export function FooterNotice({ className = "" }: { className?: string }) {
  return (
    <footer
      role="contentinfo"
      className={`border-t border-[var(--border)] bg-[var(--soft-surface)]/60 px-4 py-2.5 text-center text-xs text-[var(--muted-foreground)] flex items-center justify-center gap-2 select-none shrink-0 ${className}`}
    >
      <AlertCircle className="h-3.5 w-3.5 text-[var(--accent)] shrink-0" aria-hidden="true" />
      <span>
        <strong>Information, not legal advice:</strong> Clause risk scoring and simplifications are AI-generated for workflow convenience and do not constitute formal legal counsel.
      </span>
    </footer>
  );
}

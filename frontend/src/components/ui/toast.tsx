"use client";

import * as React from "react";
import { CheckCircle2, AlertTriangle, AlertOctagon, Info, X } from "lucide-react";

export type ToastVariant = "default" | "success" | "warning" | "error";

export interface ToastMessage {
  id: string;
  title?: string;
  description: string;
  variant?: ToastVariant;
}

interface ToastContextValue {
  toasts: ToastMessage[];
  addToast: (toast: Omit<ToastMessage, "id">) => void;
  removeToast: (id: string) => void;
}

const ToastContext = React.createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = React.useState<ToastMessage[]>([]);

  const addToast = React.useCallback(
    ({ title, description, variant = "default" }: Omit<ToastMessage, "id">) => {
      const id = Math.random().toString(36).substring(2, 9);
      setToasts((prev) => [...prev, { id, title, description, variant }]);
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, 5000);
    },
    []
  );

  const removeToast = React.useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast }}>
      {children}
      <div
        aria-live="polite"
        className="fixed bottom-4 right-4 z-50 flex flex-col space-y-2 pointer-events-none max-w-sm w-full"
      >
        {toasts.map((toast) => (
          <ToastItem key={toast.id} toast={toast} onClose={() => removeToast(toast.id)} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = React.useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return context;
}

function ToastItem({
  toast,
  onClose,
}: {
  toast: ToastMessage;
  onClose: () => void;
}) {
  const iconMap = {
    default: <Info className="h-4 w-4 text-[var(--accent)] shrink-0" />,
    success: <CheckCircle2 className="h-4 w-4 text-[var(--risk-standard-text)] shrink-0" />,
    warning: <AlertTriangle className="h-4 w-4 text-[var(--risk-unusual-text)] shrink-0" />,
    error: <AlertOctagon className="h-4 w-4 text-[var(--risk-high-text)] shrink-0" />,
  };

  return (
    <div
      role="status"
      className="pointer-events-auto flex items-start gap-3 rounded-[14px] border border-[var(--border)] bg-[var(--card)] p-4 text-[var(--foreground)] shadow-lg animate-in slide-in-from-bottom-2 duration-200"
    >
      {iconMap[toast.variant || "default"]}
      <div className="flex-1 space-y-0.5">
        {toast.title && <p className="text-xs font-semibold">{toast.title}</p>}
        <p className="text-xs text-[var(--muted-foreground)] leading-relaxed">{toast.description}</p>
      </div>
      <button
        type="button"
        onClick={onClose}
        aria-label="Close notification"
        className="text-[var(--muted-foreground)] hover:text-[var(--foreground)] p-1 rounded-[6px]"
      >
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}

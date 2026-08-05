/**
 * Application-wide constants.
 */

export const APP_NAME = process.env.NEXT_PUBLIC_APP_NAME || "Legal Document Simplifier";

export const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50 MB

export const ACCEPTED_FILE_TYPES = {
  "application/pdf": [".pdf"],
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
  "text/plain": [".txt"],
  "text/markdown": [".md"],
};

export const RISK_THRESHOLDS = {
  STANDARD: 20,
  SLIGHTLY_UNUSUAL: 40,
  ONE_SIDED: 60,
  HIGH_RISK: 80,
  UNENFORCEABLE: 100,
} as const;

export const NAV_ITEMS = [
  { label: "Dashboard", href: "/dashboard", icon: "LayoutDashboard" },
  { label: "Upload", href: "/dashboard/upload", icon: "Upload" },
  { label: "Documents", href: "/dashboard/documents", icon: "FileText" },
  { label: "Knowledge Base", href: "/dashboard/knowledge-base", icon: "Database" },
  { label: "History", href: "/dashboard/history", icon: "History" },
  { label: "Settings", href: "/dashboard/settings", icon: "Settings" },
] as const;

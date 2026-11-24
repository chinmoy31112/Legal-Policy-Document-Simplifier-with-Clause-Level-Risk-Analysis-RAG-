import type { Metadata } from "next";
<<<<<<< HEAD
import { Fraunces, Inter } from "next/font/google";
=======
>>>>>>> b678432af63f3a4eb3d5c8ec4f5040c014cfed60
import "./globals.css";
import { QueryProvider } from "@/providers/query-provider";
import { AuthProvider } from "@/providers/auth-provider";
import { ThemeProvider } from "@/components/theme/theme-provider";
import { ToastProvider } from "@/components/ui/toast";

<<<<<<< HEAD
const fraunces = Fraunces({
  subsets: ["latin"],
  weight: ["600"],
  variable: "--font-fraunces",
  display: "swap",
});

const inter = Inter({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-inter",
  display: "swap",
});

=======
>>>>>>> b678432af63f3a4eb3d5c8ec4f5040c014cfed60
export const metadata: Metadata = {
  title: "LegalSimplifier AI | Clause-Level Contract Risk Analysis & RAG",
  description:
    "AI platform for legal clause risk analysis, RAG compliance benchmarking, and automated policy simplification using Google Gemini.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
<<<<<<< HEAD
    <html
      lang="en"
      suppressHydrationWarning
      className={`${fraunces.variable} ${inter.variable}`}
    >
      <body className="min-h-screen antialiased flex flex-col font-sans selection:bg-[var(--accent)] selection:text-[var(--accent-foreground)]">
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <QueryProvider>
            <AuthProvider>
              <ToastProvider>
                {children}
              </ToastProvider>
            </AuthProvider>
          </QueryProvider>
        </ThemeProvider>
=======
    <html lang="en" className="dark">
      <body className="bg-[#070a11] text-slate-100 min-h-screen antialiased flex flex-col font-sans">
        {/* Top Government & Enterprise Compliance Banner */}
        <div className="gov-header-banner shrink-0 select-none">
          <div className="max-w-7xl mx-auto w-full flex items-center justify-between">
            <div className="flex items-center space-x-2.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400 pulse-dot"></span>
              <span className="font-semibold text-slate-300 tracking-wide text-[11px] uppercase">
                National Legal & Policy Intelligence Network
              </span>
            </div>
            <div className="hidden sm:flex items-center space-x-4 text-[11px] font-medium text-slate-400">
              <span className="flex items-center gap-1 text-emerald-400">
                <ShieldCheck className="w-3.5 h-3.5" /> Official RAG Enterprise System
              </span>
              <span className="text-slate-700">•</span>
              <span className="flex items-center gap-1 text-slate-400">
                <Lock className="w-3 h-3" /> 256-Bit Encrypted
              </span>
            </div>
          </div>
        </div>

        <QueryProvider>
          <AuthProvider>
            <div className="flex-1 flex flex-col overflow-hidden">
              {children}
            </div>
          </AuthProvider>
        </QueryProvider>
>>>>>>> b678432af63f3a4eb3d5c8ec4f5040c014cfed60
      </body>
    </html>
  );
}

import type { Metadata } from "next";
import { Manrope, Plus_Jakarta_Sans } from "next/font/google";
import "./globals.css";
import { QueryProvider } from "@/providers/query-provider";
import { AuthProvider } from "@/providers/auth-provider";
import { ShieldCheck, Lock } from "lucide-react";

const manrope = Manrope({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
  variable: "--font-manrope",
  display: "swap",
});

const plusJakartaSans = Plus_Jakarta_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
  variable: "--font-plus-jakarta",
  display: "swap",
});

export const metadata: Metadata = {
  title: "GovLegal AI | Executive Legal & Policy Intelligence Portal",
  description:
    "Production-grade AI portal for legal clause risk analysis, RAG compliance benchmark, and policy simplification using Google Gemini.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${manrope.variable} ${plusJakartaSans.variable} dark`}>
      <body className={`${plusJakartaSans.className} bg-[#070a11] text-slate-100 min-h-screen antialiased flex flex-col`}>
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
      </body>
    </html>
  );
}

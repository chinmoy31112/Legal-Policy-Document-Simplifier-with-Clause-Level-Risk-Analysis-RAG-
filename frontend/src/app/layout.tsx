import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { QueryProvider } from "@/providers/query-provider";
import { AuthProvider } from "@/providers/auth-provider";

const inter = Inter({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700", "800"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Legal Document Simplifier | AI-Powered Legal Analysis",
  description:
    "AI-powered legal document analyzer with clause-level risk assessment using Retrieval-Augmented Generation. Upload legal documents and get instant, plain-English risk analysis.",
  keywords: [
    "legal document analysis",
    "AI legal",
    "clause risk assessment",
    "RAG",
    "contract analysis",
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`dark ${inter.variable}`}>
      <body className={inter.className}>
        <QueryProvider>
          <AuthProvider>{children}</AuthProvider>
        </QueryProvider>
      </body>
    </html>
  );
}

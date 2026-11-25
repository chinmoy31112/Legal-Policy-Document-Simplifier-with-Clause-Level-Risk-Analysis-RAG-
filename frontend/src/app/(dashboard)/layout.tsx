"use client";

import * as React from "react";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { FooterNotice } from "@/components/layout/footer-notice";
import { PageTransition } from "@/components/layout/page-transition";
import { LayoutProvider } from "@/components/layout/layout-context";
import { AuthGuard } from "@/components/auth/auth-guard";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthGuard>
      <LayoutProvider>
        <div className="flex h-screen w-screen overflow-hidden bg-[var(--background)] text-[var(--foreground)]">
          {/* Left Sidebar (224px desktop, collapses to drawer on mobile) */}
          <Sidebar />

          {/* Main Content Area */}
          <div className="flex flex-1 flex-col overflow-hidden min-w-0">
            <Header />
            <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 flex flex-col">
              <PageTransition>{children}</PageTransition>
            </main>
            {/* Subtle Legal Notice Footer */}
            <FooterNotice />
          </div>
        </div>
      </LayoutProvider>
    </AuthGuard>
  );
}

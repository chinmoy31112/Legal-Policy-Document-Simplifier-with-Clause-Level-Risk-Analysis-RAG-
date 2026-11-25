"use client";

import * as React from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "@/providers/auth-provider";
import { Loader2 } from "lucide-react";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  const [hasToken] = React.useState(() => {
    if (typeof window !== "undefined") {
      return !!localStorage.getItem("access_token");
    }
    return true; // assume true during SSR to match initial render
  });

  React.useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      const searchParams = pathname && pathname !== "/" ? `?redirect=${encodeURIComponent(pathname)}` : "";
      router.replace(`/login${searchParams}`);
    } else if (!hasToken) {
      const searchParams = pathname && pathname !== "/" ? `?redirect=${encodeURIComponent(pathname)}` : "";
      router.replace(`/login${searchParams}`);
    }
  }, [isLoading, isAuthenticated, hasToken, router, pathname]);

  // If there is definitely no token, immediately return null to avoid flashing protected content
  if (!hasToken || (!isLoading && !isAuthenticated)) {
    return null;
  }

  if (isLoading) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-[var(--background)] select-none">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 animate-spin text-[var(--accent)]" />
          <p className="text-xs font-medium text-[var(--muted-foreground)]">Verifying session...</p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}

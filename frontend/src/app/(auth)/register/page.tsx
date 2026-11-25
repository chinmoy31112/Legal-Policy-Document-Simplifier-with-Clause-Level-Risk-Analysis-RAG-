"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Mail, Lock, User, Loader2, Eye, EyeOff, FileText } from "lucide-react";
import { useAuth } from "@/providers/auth-provider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function RegisterPage() {
  const { register, isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const [hasToken] = useState(() => {
    if (typeof window !== "undefined") {
      return !!localStorage.getItem("access_token");
    }
    return false;
  });

  // If already authenticated or token exists, redirect to upload immediately
  useEffect(() => {
    if ((!authLoading && isAuthenticated) || hasToken) {
      router.replace("/upload");
    }
  }, [authLoading, isAuthenticated, hasToken, router]);

  // Prevent flash of registration form while validating session or redirecting
  if (authLoading || isAuthenticated || hasToken) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--background)] select-none">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-7 h-7 animate-spin text-[var(--accent)]" />
          <p className="text-xs text-[var(--muted-foreground)]">Verifying session...</p>
        </div>
      </div>
    );
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);
    try {
      await register({ email, password, full_name: fullName });
      router.push("/login?registered=true");
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string; message?: string } }; message?: string };
      const detail =
        axiosErr?.response?.data?.detail ||
        axiosErr?.response?.data?.message ||
        axiosErr?.message ||
        "Registration failed. Please check inputs.";
      setError(detail);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 sm:p-6 bg-[var(--background)] text-[var(--foreground)] select-none">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2 }}
        className="w-full max-w-md space-y-6"
      >
        {/* Brand Header */}
        <Link href="/" className="flex items-center justify-center gap-2.5 group">
          <div className="w-10 h-10 rounded-[12px] bg-[var(--accent)] flex items-center justify-center text-[var(--accent-foreground)] shadow-xs transition-transform duration-150 group-hover:scale-105">
            <FileText className="w-5 h-5" />
          </div>
          <div>
            <div className="font-serif text-xl font-semibold tracking-tight text-[var(--foreground)]">
              LegalLens AI
            </div>
            <div className="text-[10px] font-medium text-[var(--muted-foreground)]">
              Clause Risk & Policy Simplifier
            </div>
          </div>
        </Link>

        {/* Card */}
        <div className="rounded-[18px] bg-[var(--card)] border border-[var(--border)] shadow-none p-6 sm:p-8 space-y-5">
          <div className="text-center space-y-1">
            <h2 className="font-serif text-xl font-semibold text-[var(--foreground)]">Create Your Account</h2>
            <p className="text-xs text-[var(--muted-foreground)]">
              Get started with automated contract risk analysis
            </p>
          </div>

          {error && (
            <div
              role="alert"
              className="p-3 rounded-[10px] bg-[var(--risk-high-bg)] border border-[var(--risk-high-border)] text-[var(--risk-high-text)] text-xs font-medium"
            >
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label htmlFor="reg-name" className="text-xs font-medium text-[var(--foreground)]">Full Name</label>
              <div className="relative">
                <User className="absolute left-3 top-3 w-4 h-4 text-[var(--muted-foreground)] pointer-events-none" />
                <Input
                  id="reg-name"
                  type="text"
                  required
                  placeholder="Jane Doe"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="pl-9"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label htmlFor="reg-email" className="text-xs font-medium text-[var(--foreground)]">Email Address</label>
              <div className="relative">
                <Mail className="absolute left-3 top-3 w-4 h-4 text-[var(--muted-foreground)] pointer-events-none" />
                <Input
                  id="reg-email"
                  type="email"
                  required
                  placeholder="name@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="pl-9"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label htmlFor="reg-pass" className="text-xs font-medium text-[var(--foreground)]">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-3 w-4 h-4 text-[var(--muted-foreground)] pointer-events-none" />
                <Input
                  id="reg-pass"
                  type={showPassword ? "text" : "password"}
                  required
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="pl-9 pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  className="absolute right-3 top-2.5 text-[var(--muted-foreground)] hover:text-[var(--foreground)] p-0.5 rounded-[4px]"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <Button
              type="submit"
              size="lg"
              disabled={isLoading}
              className="w-full mt-2"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin mr-1" />
                  <span>Creating Account...</span>
                </>
              ) : (
                <span>Register Workspace</span>
              )}
            </Button>
          </form>

          <div className="text-center pt-2">
            <p className="text-xs text-[var(--muted-foreground)]">
              Already have an account?{" "}
              <Link href="/login" className="text-[var(--accent)] hover:underline font-semibold">
                Sign in here
              </Link>
            </p>
          </div>
        </div>
      </motion.div>
    </div>
  );
}

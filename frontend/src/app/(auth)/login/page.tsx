"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Mail, Lock, Loader2, Eye, EyeOff, FileText } from "lucide-react";
import { useAuth } from "@/providers/auth-provider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);
    try {
      await login({ email, password });
      router.push("/dashboard");
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string; message?: string } }; message?: string };
      const detail =
        axiosErr?.response?.data?.detail ||
        axiosErr?.response?.data?.message ||
        axiosErr?.message ||
        "Invalid credentials or login failed.";
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
            <h2 className="font-serif text-xl font-semibold text-[var(--foreground)]">Welcome Back</h2>
            <p className="text-xs text-[var(--muted-foreground)]">
              Sign in to access your contract analysis workspace
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
              <label htmlFor="login-email" className="text-xs font-medium text-[var(--foreground)]">Email Address</label>
              <div className="relative">
                <Mail className="absolute left-3 top-3 w-4 h-4 text-[var(--muted-foreground)] pointer-events-none" />
                <Input
                  id="login-email"
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
              <label htmlFor="login-password" className="text-xs font-medium text-[var(--foreground)]">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-3 w-4 h-4 text-[var(--muted-foreground)] pointer-events-none" />
                <Input
                  id="login-password"
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
                  <span>Authenticating...</span>
                </>
              ) : (
                <span>Sign In to Workspace</span>
              )}
            </Button>
          </form>

          <div className="text-center pt-2">
            <p className="text-xs text-[var(--muted-foreground)]">
              Don&apos;t have an account?{" "}
              <Link href="/register" className="text-[var(--accent)] hover:underline font-semibold">
                Create one now
              </Link>
            </p>
          </div>
        </div>
      </motion.div>
    </div>
  );
}

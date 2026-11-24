"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
<<<<<<< HEAD
import { Mail, Lock, User, Loader2, Eye, EyeOff, FileText } from "lucide-react";
=======
import { Shield, Mail, Lock, User, Loader2, Eye, EyeOff, Scale } from "lucide-react";
>>>>>>> b678432af63f3a4eb3d5c8ec4f5040c014cfed60
import { useAuth } from "@/providers/auth-provider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function RegisterPage() {
  const { register } = useAuth();
  const router = useRouter();
  const [fullName, setFullName] = useState("");
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
      await register({ email, password, full_name: fullName });
      router.push("/login?registered=true");
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string; message?: string } }; message?: string };
<<<<<<< HEAD
      const detail =
        axiosErr?.response?.data?.detail ||
        axiosErr?.response?.data?.message ||
        axiosErr?.message ||
        "Registration failed. Please check inputs.";
=======
      const detail = axiosErr?.response?.data?.detail || axiosErr?.response?.data?.message || axiosErr?.message || "Registration failed. Please check inputs.";
>>>>>>> b678432af63f3a4eb3d5c8ec4f5040c014cfed60
      setError(detail);
    } finally {
      setIsLoading(false);
    }
  };

  return (
<<<<<<< HEAD
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
=======
    <div className="min-h-screen flex items-center justify-center p-6 relative bg-[#070a11] text-slate-100 select-none">
      {/* Background Soft Ambient Glows */}
      <div className="fixed inset-0 -z-10 overflow-hidden pointer-events-none">
        <div className="absolute top-[-10%] right-[20%] w-[500px] h-[500px] rounded-full bg-emerald-500/10 blur-[150px]" />
        <div className="absolute bottom-[-10%] left-[20%] w-[450px] h-[450px] rounded-full bg-indigo-500/10 blur-[150px]" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 25 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md space-y-6"
      >
        {/* Logo */}
        <div className="flex items-center justify-center gap-3">
          <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-emerald-400 to-teal-500 flex items-center justify-center shadow-lg shadow-emerald-500/20 text-slate-950 font-bold">
            <Shield className="w-6 h-6 text-slate-950" />
          </div>
          <div>
            <div className="text-xl font-extrabold font-heading tracking-tight text-white flex items-center gap-1.5">
              GovLegal <span className="text-emerald-400">AI</span>
            </div>
            <div className="text-[10px] font-bold tracking-widest text-emerald-400/90 uppercase">
              Policy & Contract Intelligence
            </div>
          </div>
        </div>

        {/* Card */}
        <div className="rounded-3xl bg-slate-900/90 border border-slate-800 shadow-2xl p-8 lg:p-9 space-y-6">
          <div className="text-center space-y-1">
            <h2 className="text-2xl font-bold font-heading text-slate-100">Create Account</h2>
            <p className="text-xs text-slate-400">
              Set up your legal analysis credentials
>>>>>>> b678432af63f3a4eb3d5c8ec4f5040c014cfed60
            </p>
          </div>

          {error && (
<<<<<<< HEAD
            <div
              role="alert"
              className="p-3 rounded-[10px] bg-[var(--risk-high-bg)] border border-[var(--risk-high-border)] text-[var(--risk-high-text)] text-xs font-medium"
            >
=======
            <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-xs font-medium">
>>>>>>> b678432af63f3a4eb3d5c8ec4f5040c014cfed60
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
<<<<<<< HEAD
            <div className="space-y-1.5">
              <label htmlFor="reg-name" className="text-xs font-medium text-[var(--foreground)]">Full Name</label>
              <div className="relative">
                <User className="absolute left-3 top-3 w-4 h-4 text-[var(--muted-foreground)] pointer-events-none" />
                <Input
                  id="reg-name"
=======
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-1.5">
                Full Name
              </label>
              <div className="relative">
                <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input
>>>>>>> b678432af63f3a4eb3d5c8ec4f5040c014cfed60
                  type="text"
                  required
                  placeholder="Jane Doe"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
<<<<<<< HEAD
                  className="pl-9"
=======
                  placeholder="Review Officer Name"
                  required
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-100 placeholder:text-slate-500 focus:border-emerald-500 focus:outline-none transition-all"
>>>>>>> b678432af63f3a4eb3d5c8ec4f5040c014cfed60
                />
              </div>
            </div>

<<<<<<< HEAD
            <div className="space-y-1.5">
              <label htmlFor="reg-email" className="text-xs font-medium text-[var(--foreground)]">Email Address</label>
              <div className="relative">
                <Mail className="absolute left-3 top-3 w-4 h-4 text-[var(--muted-foreground)] pointer-events-none" />
                <Input
                  id="reg-email"
=======
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-1.5">
                Email Address
              </label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input
>>>>>>> b678432af63f3a4eb3d5c8ec4f5040c014cfed60
                  type="email"
                  required
                  placeholder="name@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
<<<<<<< HEAD
                  className="pl-9"
=======
                  placeholder="officer@example.com"
                  required
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-100 placeholder:text-slate-500 focus:border-emerald-500 focus:outline-none transition-all"
>>>>>>> b678432af63f3a4eb3d5c8ec4f5040c014cfed60
                />
              </div>
            </div>

<<<<<<< HEAD
            <div className="space-y-1.5">
              <label htmlFor="reg-pass" className="text-xs font-medium text-[var(--foreground)]">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-3 w-4 h-4 text-[var(--muted-foreground)] pointer-events-none" />
                <Input
                  id="reg-pass"
=======
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-1.5">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input
>>>>>>> b678432af63f3a4eb3d5c8ec4f5040c014cfed60
                  type={showPassword ? "text" : "password"}
                  required
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
<<<<<<< HEAD
                  className="pl-9 pr-10"
=======
                  placeholder="••••••••••••"
                  required
                  minLength={8}
                  className="w-full pl-10 pr-10 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-100 placeholder:text-slate-500 focus:border-emerald-500 focus:outline-none transition-all"
>>>>>>> b678432af63f3a4eb3d5c8ec4f5040c014cfed60
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
<<<<<<< HEAD
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  className="absolute right-3 top-2.5 text-[var(--muted-foreground)] hover:text-[var(--foreground)] p-0.5 rounded-[4px]"
=======
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
>>>>>>> b678432af63f3a4eb3d5c8ec4f5040c014cfed60
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <Button
              type="submit"
              size="lg"
              disabled={isLoading}
<<<<<<< HEAD
              className="w-full mt-2"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin mr-1" />
                  <span>Creating Account...</span>
                </>
              ) : (
                <span>Register Workspace</span>
=======
              className="w-full h-11 rounded-xl text-xs font-bold uppercase tracking-wider bg-gradient-to-r from-emerald-400 to-teal-400 text-slate-950 hover:from-emerald-300 hover:to-teal-300 shadow-lg shadow-emerald-500/20 transition-all duration-300 flex items-center justify-center gap-2 disabled:opacity-50 mt-2"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin text-slate-950" />
                  Creating Account...
                </>
              ) : (
                "Complete Registration"
>>>>>>> b678432af63f3a4eb3d5c8ec4f5040c014cfed60
              )}
            </Button>
          </form>

<<<<<<< HEAD
          <div className="text-center pt-2">
            <p className="text-xs text-[var(--muted-foreground)]">
              Already have an account?{" "}
              <Link href="/login" className="text-[var(--accent)] hover:underline font-semibold">
                Sign in here
              </Link>
            </p>
          </div>
=======
          <div className="pt-4 border-t border-slate-800 text-center text-xs text-slate-400">
            Already registered?{" "}
            <Link href="/login" className="text-emerald-400 hover:underline font-bold">
              Sign In
            </Link>
          </div>
        </div>

        {/* Legal Notice */}
        <div className="p-3.5 rounded-2xl bg-slate-900/60 border border-slate-800 text-slate-400 text-[11px] flex items-center gap-2.5">
          <Scale className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>Informational legal simplification only. Does not constitute formal legal advice.</span>
>>>>>>> b678432af63f3a4eb3d5c8ec4f5040c014cfed60
        </div>
      </motion.div>
    </div>
  );
}

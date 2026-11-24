"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Shield, Mail, Lock, User, Loader2, Eye, EyeOff, Scale } from "lucide-react";
import { useAuth } from "@/providers/auth-provider";

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
      const detail = axiosErr?.response?.data?.detail || axiosErr?.response?.data?.message || axiosErr?.message || "Registration failed. Please check inputs.";
      setError(detail);
    } finally {
      setIsLoading(false);
    }
  };

  return (
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
            </p>
          </div>

          {error && (
            <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-xs font-medium">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-1.5">
                Full Name
              </label>
              <div className="relative">
                <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Review Officer Name"
                  required
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-100 placeholder:text-slate-500 focus:border-emerald-500 focus:outline-none transition-all"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-1.5">
                Email Address
              </label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="officer@example.com"
                  required
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-100 placeholder:text-slate-500 focus:border-emerald-500 focus:outline-none transition-all"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-1.5">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  required
                  minLength={8}
                  className="w-full pl-10 pr-10 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-100 placeholder:text-slate-500 focus:border-emerald-500 focus:outline-none transition-all"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full h-11 rounded-xl text-xs font-bold uppercase tracking-wider bg-gradient-to-r from-emerald-400 to-teal-400 text-slate-950 hover:from-emerald-300 hover:to-teal-300 shadow-lg shadow-emerald-500/20 transition-all duration-300 flex items-center justify-center gap-2 disabled:opacity-50 mt-2"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin text-slate-950" />
                  Creating Account...
                </>
              ) : (
                "Complete Registration"
              )}
            </button>
          </form>

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
        </div>
      </motion.div>
    </div>
  );
}

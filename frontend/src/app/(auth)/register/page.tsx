"use client";

/**
 * Registration page.
 */

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Shield, Mail, Lock, User, Loader2, Eye, EyeOff } from "lucide-react";
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
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-6 relative bg-[#f8faf3]">
      {/* Background Soft Glows */}
      <div className="fixed inset-0 -z-10 overflow-hidden pointer-events-none">
        <div className="absolute top-[-10%] right-[20%] w-[500px] h-[500px] rounded-full bg-[#d9e7cd]/35 blur-[130px]" />
        <div className="absolute bottom-[-10%] left-[20%] w-[450px] h-[450px] rounded-full bg-[#fed7d2]/30 blur-[130px]" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="w-full max-w-md"
      >
        {/* Logo */}
        <div className="flex items-center justify-center gap-3 mb-8">
          <div className="w-11 h-11 rounded-2xl bg-[#55624d] flex items-center justify-center shadow-ambient">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <span className="text-xl font-bold font-display tracking-tight text-[#191c18]">
            Legal<span className="text-[#55624d]">Sanctuary</span>
          </span>
        </div>

        {/* Card */}
        <div className="rounded-3xl bg-white shadow-ambient-lg p-9 border border-white/80">
          <h2 className="text-2xl font-bold font-display text-center mb-2 text-[#191c18]">
            Create Account
          </h2>
          <p className="text-sm text-[#74796e] text-center mb-8">
            Begin simplified legal document analysis
          </p>

          {error && (
            <div className="mb-6 p-4 rounded-2xl bg-[#fed7d2]/50 text-sm text-[#755754] font-medium">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Full Name */}
            <div>
              <label className="block text-sm font-semibold text-[#444841] mb-2">
                Full Name
              </label>
              <div className="relative">
                <User className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-[#74796e]" />
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Sarah Jenkins"
                  required
                  className="w-full pl-11 pr-4 py-3 rounded-2xl bg-[#f2f4ed] text-sm text-[#191c18] placeholder:text-[#74796e] focus:bg-[#d9e7cd] focus:outline-none transition-all duration-400"
                />
              </div>
            </div>

            {/* Email */}
            <div>
              <label className="block text-sm font-semibold text-[#444841] mb-2">
                Email Address
              </label>
              <div className="relative">
                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-[#74796e]" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  required
                  className="w-full pl-11 pr-4 py-3 rounded-2xl bg-[#f2f4ed] text-sm text-[#191c18] placeholder:text-[#74796e] focus:bg-[#d9e7cd] focus:outline-none transition-all duration-400"
                />
              </div>
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm font-semibold text-[#444841] mb-2">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-[#74796e]" />
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Min. 8 characters"
                  required
                  minLength={8}
                  className="w-full pl-11 pr-11 py-3 rounded-2xl bg-[#f2f4ed] text-sm text-[#191c18] placeholder:text-[#74796e] focus:bg-[#d9e7cd] focus:outline-none transition-all duration-400"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2"
                >
                  {showPassword ? (
                    <EyeOff className="w-4 h-4 text-[#74796e]" />
                  ) : (
                    <Eye className="w-4 h-4 text-[#74796e]" />
                  )}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-3.5 rounded-2xl text-sm font-semibold text-white bg-[#55624d] hover:bg-[#45513d] shadow-ambient transition-all duration-300 disabled:opacity-50"
            >
              {isLoading ? (
                <span className="flex items-center justify-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin text-white" />
                  Creating account...
                </span>
              ) : (
                "Create Account"
              )}
            </button>
          </form>

          <p className="text-sm text-[#74796e] text-center mt-7">
            Already have an account?{" "}
            <Link
              href="/login"
              className="text-[#55624d] hover:underline font-semibold transition-colors"
            >
              Sign in
            </Link>
          </p>
        </div>
      </motion.div>
    </div>
  );
}


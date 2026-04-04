"use client";

import React, { useState, useEffect } from "react";
import { signInWithPopup } from "firebase/auth";
import { auth, googleProvider } from "@/lib/firebase";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth/AuthContext";
import { ShieldCheck, ChevronRight, BarChart3, LockKeyhole, Sparkles } from "lucide-react";

export default function LoginPage() {
  const { user, loading } = useAuth();
  const [error, setError] = useState("");
  const [isSigningIn, setIsSigningIn] = useState(false);
  const router = useRouter();

  useEffect(() => {
    if (user && !loading) {
      router.push("/dashboard");
    }
  }, [user, loading, router]);

  const handleGoogleLogin = async () => {
    setIsSigningIn(true);
    setError("");
    try {
      await signInWithPopup(auth, googleProvider);
    } catch (err: any) {
      setError(err.message || "Failed to sign in with Google.");
    } finally {
      setIsSigningIn(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0F172A] flex flex-col items-center justify-center">
        <div className="relative w-24 h-24">
          <div className="absolute inset-0 border-4 border-slate-800 rounded-full"></div>
          <div className="absolute inset-0 border-4 border-blue-500 rounded-full border-t-transparent animate-spin"></div>
          <ShieldCheck className="absolute inset-0 m-auto h-10 w-10 text-blue-500 animate-pulse" />
        </div>
        <p className="mt-8 text-slate-400 font-bold tracking-[0.2em] uppercase text-xs">Initializing Secure Core...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#020617] text-slate-200 flex items-center justify-center p-6 relative overflow-hidden">
      {/* Dynamic Background Effects */}
      <div className="absolute top-0 left-0 w-full h-full pointer-events-none overflow-hidden">
        <div className="absolute top-[-20%] left-[-10%] w-[60%] h-[60%] bg-blue-600/10 rounded-full blur-[120px] animate-pulse"></div>
        <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-cyan-600/10 rounded-full blur-[100px] delay-1000"></div>
        <div className="absolute inset-0 opacity-[0.03] bg-[url('https://www.transparenttextures.com/patterns/carbon-fibre.png')]"></div>
      </div>

      <div className="max-w-[1200px] w-full grid lg:grid-cols-2 gap-12 items-center relative z-10">

        {/* Left Side: Branding Content */}
        <div className="hidden lg:flex flex-col space-y-12 pr-12">
          <div>
            <div className="inline-flex items-center gap-3 px-4 py-2 bg-blue-500/10 border border-blue-500/20 rounded-full mb-6">
              <Sparkles className="h-4 w-4 text-blue-400" />
              <span className="text-[10px] uppercase font-black tracking-widest text-blue-300">Alpha Release 1.0</span>
            </div>
            <h1 className="text-7xl font-black tracking-tight leading-[0.95] text-white">
              FINCORE
            </h1>
            <p className="mt-8 text-xl text-slate-400 leading-relaxed max-w-lg">
              The next-generation Command Center for <span className="text-white font-bold">Banking Intelligence</span> and Working Capital Management.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-6">
            {[
              { icon: BarChart3, label: "Real-time Metrics", desc: "CC & WCDL interest tracking." },
              { icon: LockKeyhole, label: "Secure Gateway", desc: "Enterprise-grade Auth protocols." }
            ].map((item, i) => (
              <div key={i} className="p-6 rounded-3xl bg-slate-900/40 border border-slate-800/50 backdrop-blur-xl group hover:border-blue-500/30 transition-all">
                <item.icon className="h-8 w-8 text-blue-500 mb-4 group-hover:scale-110 transition-transform" />
                <h4 className="font-bold text-white mb-1">{item.label}</h4>
                <p className="text-xs text-slate-500 leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Right Side: Login Card */}
        <div className="flex justify-center lg:justify-end">
          <div className="w-full max-w-md p-10 lg:p-12 rounded-[40px] bg-[#0F172A] border border-slate-800/50 shadow-2xl relative group overflow-hidden">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-blue-500 to-transparent opacity-50"></div>

            <div className="flex flex-col items-center text-center mb-12">
              <div className="h-20 w-20 bg-blue-500/10 rounded-3xl flex items-center justify-center mb-6 border border-blue-500/20 group-hover:rotate-6 transition-transform">
                <ShieldCheck className="h-10 w-10 text-blue-500" />
              </div>
              <h2 className="text-3xl font-black text-white tracking-tight mb-2">Welcome Back</h2>
              <p className="text-slate-500 font-medium">Verify your identity to enter the Core</p>
            </div>

            {error && (
              <div className="mb-8 p-4 bg-red-500/10 border border-red-500/20 rounded-2xl text-red-400 text-xs text-center font-bold">
                {error}
              </div>
            )}

            <button
              onClick={handleGoogleLogin}
              disabled={isSigningIn}
              className="group w-full relative flex items-center justify-center gap-4 bg-white text-[#0F172A] font-black py-5 px-6 rounded-2xl transition-all hover:bg-blue-50 active:scale-95 disabled:opacity-50 overflow-hidden shadow-[0_0_40px_rgba(255,255,255,0.05)]"
            >
              {isSigningIn ? (
                <div className="h-6 w-6 border-3 border-[#0F172A] border-t-transparent rounded-full animate-spin"></div>
              ) : (
                <>
                  <svg width="24" height="24" viewBox="0 0 48 48">
                    <path fill="#FFC107" d="M43.611,20.083H42V20H24v8h11.303c-1.649,4.657-6.08,8-11.303,8c-6.627,0-12-5.373-12-12c0-6.627,5.373-12,12-12c3.059,0,5.842,1.154,7.961,3.039l5.657-5.657C34.046,6.053,29.268,4,24,4C12.955,4,4,12.955,4,24c0,11.045,8.955,20,20,20c11.045,0,20-8.955,20-20C44,22.659,43.862,21.35,43.611,20.083z" />
                    <path fill="#FF3D00" d="M6.306,14.691l6.571,4.819C14.655,15.108,18.961,12,24,12c3.059,0,5.842,1.154,7.961,3.039l5.657-5.657C34.046,6.053,29.268,4,24,4C16.318,4,9.656,8.337,6.306,14.691z" />
                    <path fill="#4CAF50" d="M24,44c5.166,0,9.86-1.977,13.409-5.192l-6.19-5.238C29.211,35.091,26.715,36,24,36c-5.202,0-9.619-3.317-11.283-7.946l-6.522,5.025C9.505,39.556,16.227,44,24,44z" />
                    <path fill="#1976D2" d="M43.611,20.083H42V20H24v8h11.303c-0.792,2.237-2.231,4.166-4.087,5.571c0.001-0.001,0.002-0.001,0.003-0.002l6.19,5.238C36.971,39.205,44,34,44,24C44,22.659,43.862,21.35,43.611,20.083z" />
                  </svg>
                  <span className="uppercase tracking-widest text-sm">Secure Entry with Google</span>
                  <ChevronRight className="h-5 w-5 text-[#0F172A]/30 group-hover:translate-x-1 transition-transform" />
                </>
              )}
            </button>

            <div className="mt-12 flex flex-col items-center space-y-4">
              <p className="text-slate-600 text-[10px] font-black uppercase tracking-[0.3em]">Licensed to Financial Experts Only</p>
              <div className="flex gap-2">
                <div className="h-1 w-8 bg-blue-600 rounded-full"></div>
                <div className="h-1 w-2 bg-slate-800 rounded-full"></div>
                <div className="h-1 w-2 bg-slate-800 rounded-full"></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

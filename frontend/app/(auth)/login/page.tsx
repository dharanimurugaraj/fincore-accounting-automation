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
      if (!auth) {
        throw new Error("Firebase Auth is not initialized.");
      }
      await signInWithPopup(auth, googleProvider);
    } catch (err: any) {
      setError(err.message || "Failed to sign in with Google.");
    } finally {
      setIsSigningIn(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-neutral-app flex flex-col items-center justify-center">
        <div className="w-16 h-16 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
        <p className="mt-6 text-t-muted font-bold tracking-widest uppercase text-xs">Initializing Secure Core...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-neutral-app text-t-body flex items-center justify-center p-6 relative overflow-hidden">
      {/* Subtle Background Decor */}
      <div className="absolute top-0 left-0 w-full h-full pointer-events-none">
        <div className="absolute -top-[10%] -left-[10%] w-[40%] h-[40%] bg-primary/5 rounded-full blur-[120px]"></div>
        <div className="absolute -bottom-[10%] -right-[10%] w-[40%] h-[40%] bg-ai-teal/5 rounded-full blur-[120px]"></div>
      </div>

      <div className="max-w-[1100px] w-full grid lg:grid-cols-2 gap-16 items-center relative z-10">
        
        {/* Left: Branding & Value Prop */}
        <div className="hidden lg:block space-y-10">
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-primary-subtle border border-primary/10 rounded-full">
            <Sparkles className="h-3.5 w-3.5 text-primary" />
            <span className="text-[10px] font-bold uppercase tracking-wider text-primary">Enterprise Release 1.0</span>
          </div>
          
          <div className="space-y-4">
            <h1 className="text-6xl font-black tracking-tight text-t-heading leading-tight">
              Intelligence at the <br />
              <span className="text-primary italic">FinCore</span> of Banking.
            </h1>
            <p className="text-lg text-t-muted max-w-md leading-relaxed">
              Automated Working Capital Management, CC/WCDL tracking, and AI-powered financial reporting in one secure command center.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            {[
              { icon: BarChart3, label: "Real-time Metrics", desc: "Automated CC & WCDL snapshots." },
              { icon: LockKeyhole, label: "Bank Security", desc: "Enterprise-grade Auth encryption." }
            ].map((item, i) => (
              <div key={i} className="p-6 rounded-2xl bg-white border border-neutral-border shadow-sm">
                <item.icon className="h-6 w-6 text-primary mb-3" />
                <h4 className="font-bold text-t-heading text-sm">{item.label}</h4>
                <p className="text-xs text-t-muted mt-1 leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Right: Modern Login Card */}
        <div className="flex justify-center lg:justify-end">
          <div className="w-full max-w-md bg-white border border-neutral-border rounded-[32px] p-10 lg:p-12 shadow-2xl relative">
            <div className="flex flex-col items-center mb-10 text-center">
              <div className="flex items-center gap-2 mb-6">
                 <img src="/icon.png" alt="FinCore" className="h-10 w-10" />
                 <span className="text-xl font-black text-t-heading tracking-tighter italic">FINCORE</span>
              </div>
              <h2 className="text-2xl font-black text-t-heading tracking-tight mb-2">Welcome Back</h2>
              <p className="text-t-muted text-sm px-4">Access your organization&apos;s financial control center.</p>
            </div>

            {error && (
              <div className="mb-6 p-4 bg-status-critical-bg border border-status-critical/20 rounded-xl text-status-critical text-xs text-center font-bold">
                {error}
              </div>
            )}

            <button
              onClick={handleGoogleLogin}
              disabled={isSigningIn}
              className="group w-full flex items-center justify-center gap-3 bg-neutral-app border border-neutral-border text-t-heading font-bold py-4 rounded-xl transition-all hover:bg-neutral-row active:scale-[0.98] disabled:opacity-50"
            >
              {isSigningIn ? (
                <div className="h-5 w-5 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
              ) : (
                <>
                  <svg width="20" height="20" viewBox="0 0 48 48">
                    <path fill="#FFC107" d="M43.611,20.083H42V20H24v8h11.303c-1.649,4.657-6.08,8-11.303,8c-6.627,0-12-5.373-12-12c0-6.627,5.373-12,12-12c3.059,0,5.842,1.154,7.961,3.039l5.657-5.657C34.046,6.053,29.268,4,24,4C12.955,4,4,12.955,4,24c0,11.045,8.955,20,20,20c11.045,0,20-8.955,20-20C44,22.659,43.862,21.35,43.611,20.083z" />
                    <path fill="#FF3D00" d="M6.306,14.691l6.571,4.819C14.655,15.108,18.961,12,24,12c3.059,0,5.842,1.154,7.961,3.039l5.657-5.657C34.046,6.053,29.268,4,24,4C16.318,4,9.656,8.337,6.306,14.691z" />
                    <path fill="#4CAF50" d="M24,44c5.166,0,9.86-1.977,13.409-5.192l-6.19-5.238C29.211,35.091,26.715,36,24,36c-5.202,0-9.619-3.317-11.283-7.946l-6.522,5.025C9.505,39.556,16.227,44,24,44z" />
                    <path fill="#1976D2" d="M43.611,20.083H42V20H24v8h11.303c-0.792,2.237-2.231,4.166-4.087,5.571c0.001-0.001,0.002-0.001,0.003-0.002l6.19,5.238C36.971,39.205,44,34,44,24C44,22.659,43.862,21.35,43.611,20.083z" />
                  </svg>
                  <span className="text-sm font-bold">Continue with Google</span>
                  <ChevronRight className="h-4 w-4 text-t-muted group-hover:translate-x-1 transition-all" />
                </>
              )}
            </button>

            <div className="mt-12 flex flex-col items-center">
              <span className="text-[10px] font-black uppercase tracking-[0.2em] text-t-muted">Powered by Vyrenzo AI</span>
              <div className="flex gap-1.5 mt-3">
                <div className="h-1 w-3 bg-primary rounded-full"></div>
                <div className="h-1 w-1 bg-neutral-row rounded-full"></div>
                <div className="h-1 w-1 bg-neutral-row rounded-full"></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

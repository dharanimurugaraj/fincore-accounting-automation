"use client";

import Link from "next/link";
import { MoveLeft, HelpCircle } from "lucide-react";

export default function NotFound() {
  return (
    <div className="min-h-screen bg-neutral-app flex flex-col items-center justify-center p-6 text-center">
      {/* Premium Background Glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-blue-600/10 rounded-full blur-[120px] pointer-events-none"></div>
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[300px] h-[300px] bg-ai-violet/5 rounded-full blur-[80px] pointer-events-none"></div>

      <div className="relative z-10 max-w-md w-full space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
        <div className="w-24 h-24 bg-neutral-card border border-neutral-border rounded-3xl flex items-center justify-center mx-auto shadow-2xl">
          <HelpCircle className="w-12 h-12 text-ai-violet animate-pulse" />
        </div>

        <div className="space-y-3">
          <h1 className="text-4xl font-bold text-t-heading tracking-tight">404 — Missing Route</h1>
          <p className="text-t-muted text-lg leading-relaxed">
            The page you are looking for doesn&apos;t exist or has been relocated within the Vyrenzo platform.
          </p>
        </div>

        <div className="pt-4">
          <Link 
            href="/dashboard"
            className="inline-flex items-center gap-2 px-8 py-4 bg-ai-violet hover:bg-ai-violet text-t-heading font-semibold rounded-2xl transition-all shadow-lg shadow-indigo-600/20 active:scale-[0.98]"
          >
            <MoveLeft className="w-5 h-5" />
            Return to Dashboard
          </Link>
        </div>

        <p className="text-t-muted text-sm font-medium tracking-wide pt-8">
            VYRENZO FINCORE — ENTERPRISE LAYER
        </p>
      </div>
    </div>
  );
}

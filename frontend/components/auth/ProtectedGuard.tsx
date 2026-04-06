"use client";

import { useAuth } from "@/components/auth/AuthContext";
import { useRouter, usePathname } from "next/navigation";
import { useEffect } from "react";

export default function ProtectedGuard({ children }: { children: React.ReactNode }) {
  const { user, profile, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && !user) {
      // Redirect to login if user is not authenticated and trying to access a protected route
      router.push("/login");
    }
  }, [user, loading, router]);

  if (loading) {
     return (
      <div className="min-h-screen bg-neutral-app flex flex-col items-center justify-center">
        <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
        <p className="mt-4 text-t-muted font-semibold tracking-tight">Authenticating identity...</p>
      </div>
    );
  }

  // If there's no user, we don't render anything while the redirect happens
  if (!user) {
    return null;
  }

  // Enforce Dynamic Approval Queue (Role 4 Fallback)
  if (profile?.role === "PENDING_APPROVAL") {
    return (
      <div className="min-h-screen bg-neutral-app flex flex-col items-center justify-center p-8">
        <div className="max-w-md w-full bg-neutral-card border border-neutral-border rounded-2xl p-8 text-center space-y-6 shadow-2xl">
           <div className="w-16 h-16 bg-status-critical/10 rounded-full flex items-center justify-center mx-auto border border-rose-500/20">
              <svg className="w-8 h-8 text-status-critical" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
           </div>
           
           <h2 className="text-2xl font-bold text-t-heading tracking-tight">Access Restricted</h2>
           <p className="text-t-muted text-sm leading-relaxed">
             Your account identity has been verified, but your organizational access is currently <strong>awaiting administrator approval.</strong> 
           </p>
           
           <div className="pt-4 border-t border-neutral-border">
               <button 
                  onClick={() => {
                      import("@/lib/firebase").then(({ auth }) => {
                          if (auth) auth.signOut();
                      });
                  }}
                  className="px-6 py-2 bg-neutral-row hover:bg-neutral-border text-t-body font-medium rounded-lg transition-colors w-full"
               >
                   Sign Out
               </button>
           </div>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}

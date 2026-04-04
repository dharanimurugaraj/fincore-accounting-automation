"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth/AuthContext";

/**
 * Root Landing Logic:
 * Automatically routes users to the Dashboard if logged in, 
 * or the Premium Login Screen if not.
 */
export default function RootPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading) {
      if (user) {
        router.push("/dashboard");
      } else {
        router.push("/login");
      }
    }
  }, [user, loading, router]);

  // Premium loading state while deciding where to send the user
  return (
    <div className="min-h-screen bg-white flex flex-col items-center justify-center">
      <div className="relative w-16 h-16">
        <div className="absolute inset-0 border-4 border-blue-50 rounded-full"></div>
        <div className="absolute inset-0 border-4 border-blue-600 rounded-full border-t-transparent animate-spin"></div>
      </div>
      <p className="mt-6 text-slate-400 font-medium tracking-tight animate-pulse">Launching Vyrenzo...</p>
    </div>
  );
}

"use client";

import { useAuth } from "@/components/auth/AuthContext";
import { useRouter, usePathname } from "next/navigation";
import { useEffect } from "react";

export default function ProtectedGuard({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
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
      <div className="min-h-screen bg-white flex flex-col items-center justify-center">
        <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
        <p className="mt-4 text-slate-500 font-medium">Loading Dashboard...</p>
      </div>
    );
  }

  // If there's no user, we don't render anything while the redirect happens
  if (!user) {
    return null;
  }

  return <>{children}</>;
}

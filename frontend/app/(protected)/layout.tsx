"use client";

import Sidebar from "@/components/layout/Sidebar";
import TopBar from "@/components/layout/TopBar";
import Footer from "@/components/layout/Footer";
import ProtectedGuard from "@/components/auth/ProtectedGuard";
import { LayoutProvider, useLayout } from "@/components/layout/LayoutContext";

function DashboardContent({ children }: { children: React.ReactNode }) {
  const { collapsed } = useLayout();

  return (
    <div className="min-h-screen bg-neutral-app transition-colors duration-500 overflow-x-hidden">
      <Sidebar />
      <div 
        className={`flex min-h-screen flex-col transition-all duration-500 ease-in-out ${
          collapsed ? "pl-16" : "pl-64"
        }`}
      >
        <TopBar />
        <main className="flex-1 p-8 text-t-body overflow-y-auto">{children}</main>
        <Footer />
      </div>
    </div>
  );
}


export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ProtectedGuard>
      <LayoutProvider>
        <DashboardContent>{children}</DashboardContent>
      </LayoutProvider>
    </ProtectedGuard>
  );
}


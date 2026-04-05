import Sidebar from "@/components/layout/Sidebar";
import TopBar from "@/components/layout/TopBar";
import Footer from "@/components/layout/Footer";
import ProtectedGuard from "@/components/auth/ProtectedGuard";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ProtectedGuard>
      <div className="min-h-screen bg-[#0F172A] text-slate-200">
        <Sidebar />
        <div className="ml-64 flex min-h-screen flex-col">
          <TopBar />
          <main className="flex-1 p-8">{children}</main>
          <Footer />
        </div>
      </div>
    </ProtectedGuard>
  );
}

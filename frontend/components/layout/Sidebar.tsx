"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Upload,
  FileText,
  BarChart3,
  Settings,
  ChevronLeft,
  Briefcase,
  Globe,
  Calculator,
  Cpu,
  Activity,
  ShieldCheck,
  Users,
  UserCog
} from "lucide-react";
import { useState } from "react";
import { useAuth } from "@/components/auth/AuthContext";

const CORE_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/upload", label: "Upload", icon: Upload },
  { href: "/documents", label: "Documents", icon: FileText }
];

const ANALYTICS_ITEMS = [
  { href: "/reports", label: "Reports", icon: BarChart3 },
  { href: "/wcdl", label: "WCDL Tracker", icon: Briefcase },
  { href: "/forex", label: "Forex Register", icon: Globe }
];

const SYSTEM_ITEMS = [
  { href: "/activity", label: "Activity", icon: Activity },
  { href: "/audit-logs", label: "Audit Logs", icon: ShieldCheck },
  { href: "/settings", label: "Settings", icon: Settings }
];

const adminItems = [
  { href: "/admin/roles", label: "Role Management", icon: Users },
  { href: "/admin/users", label: "User Management", icon: UserCog },
  { href: "/admin/formulas", label: "Formula Logic", icon: Calculator },
  { href: "/admin/models", label: "AI Model Config", icon: Cpu },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const { profile } = useAuth();

  const canShow = (label: string) => {
    if (!profile) return false;
    if (profile.role_id === 0) return true; 
    if (profile.allowed_pages?.includes("*")) return true;
    return profile.allowed_pages?.includes(label);
  };

  const NavGroup = ({ title, items }: { title: string, items: any[] }) => {
    const visibleItems = items.filter(item => canShow(item.label));
    if (visibleItems.length === 0) return null;
    
    return (
      <div className="mb-4">
        {!collapsed && (
          <div className="px-3 mb-2 text-[10px] uppercase tracking-widest text-slate-500 font-bold">
            {title}
          </div>
        )}
        <div className="space-y-1">
          {visibleItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-cyan-500/10 text-cyan-400 font-bold"
                    : "text-slate-400 hover:bg-slate-800/50 hover:text-slate-200"
                }`}
              >
                <item.icon className="h-5 w-5 shrink-0" />
                {!collapsed && <span>{item.label}</span>}
              </Link>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <aside
      className={`fixed left-0 top-0 z-40 h-screen border-r border-slate-800 bg-slate-950 transition-all duration-300 ${
        collapsed ? "w-16" : "w-64"
      }`}
    >
      <div className="flex h-16 items-center justify-between border-b border-slate-800 px-4">
        {!collapsed && (
          <Link href="/dashboard" className="flex items-center gap-2">
            <img src="/icon.png" alt="FinCore" className="h-8 w-8 object-contain" />
            <span className="text-lg font-bold text-slate-100 uppercase tracking-widest">FinCore</span>
          </Link>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="rounded-md p-1.5 text-slate-400 hover:bg-slate-800 hover:text-slate-200"
        >
          <ChevronLeft
            className={`h-4 w-4 transition-transform ${
              collapsed ? "rotate-180" : ""
            }`}
          />
        </button>
      </div>

      <nav className="mt-6 px-2 overflow-y-auto h-[calc(100vh-5rem)] scrollbar-hide pb-10">
        <NavGroup title="Core Platform" items={CORE_ITEMS} />
        <NavGroup title="Financial Pipelines" items={ANALYTICS_ITEMS} />
        <NavGroup title="System & Policy" items={SYSTEM_ITEMS} />

        {/* Admin Section */}
        {profile?.role_id === 0 && (
          <div className="pt-2 mt-2 border-t border-slate-800/50">
            {!collapsed && <div className="mt-4 mb-2 px-3 text-[10px] uppercase tracking-widest text-indigo-500 font-bold">Domain Configuration</div>}
            {adminItems.map((item) => {
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-indigo-500/10 text-indigo-400 font-bold"
                      : "text-slate-400 hover:bg-slate-800/50 hover:text-slate-200"
                  }`}
                >
                  <item.icon className="h-5 w-5 shrink-0" />
                  {!collapsed && <span>{item.label}</span>}
                </Link>
              );
            })}
          </div>
        )}
      </nav>
    </aside>
  );
}

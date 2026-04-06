"use client";

import { Bell, Search, User, LogOut } from "lucide-react";
import { useAuth } from "@/components/auth/AuthContext";

export default function TopBar() {
  const { user, profile, logout } = useAuth();

  return (
    <header className="sticky top-0 z-30 flex h-20 items-center justify-between border-b border-neutral-border bg-neutral-card px-8 shadow-sm">
      <div className="flex items-center gap-6">
        <div className="relative">
          <Search className="absolute left-3.5 top-1/2 h-4.5 w-4.5 -translate-y-1/2 text-t-muted" />
          <input
            type="text"
            placeholder="Search documents, reports, etc..."
            className="h-11 w-80 rounded-xl border border-neutral-border/50 bg-neutral-card/50 pl-11 pr-4 text-sm text-t-heading placeholder-slate-500 outline-none focus:border-blue-500/50 focus:ring-4 focus:ring-blue-500/10 transition-all shadow-inner"
          />
        </div>
      </div>

      <div className="flex items-center gap-4">
        <button className="relative rounded-xl p-2.5 text-t-muted hover:bg-neutral-row hover:text-t-heading transition-sm">
          <Bell className="h-5 w-5" />
          <span className="absolute right-2.5 top-2.5 h-2 w-2 rounded-full bg-primary" />
        </button>

        <div className="h-8 w-px bg-neutral-row mx-2" />

        <div className="flex items-center gap-4">
          <div className="flex flex-col items-end hidden sm:flex leading-none">
             <span className="text-sm font-bold text-t-heading tracking-tight">{user?.displayName || "User"}</span>
             <span className={`text-[9px] font-bold uppercase tracking-widest mt-1 px-1.5 py-0.5 rounded ${
                profile?.role_id === 0 ? "bg-status-medium-bg text-status-medium border border-amber-500/20" : "text-t-muted"
             }`}>
               {profile?.role ? `Vyrenzo ${profile.role.replace("_", " ")}` : "Authenticating..."}
             </span>
          </div>

          <div className="group relative">
            <button className="flex items-center gap-2 rounded-xl p-1 text-t-body hover:bg-neutral-row transition-all border border-neutral-border">
                {user?.photoURL ? (
                    <img src={user.photoURL} alt="Avatar" className="h-9 w-9 rounded-lg border border-neutral-border" />
                ) : (
                    <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary-subtle border border-primary/10">
                    <User className="h-5 w-5 text-primary" />
                    </div>
                )}
            </button>
            
            {/* Simple logout tooltip/menu on hover or click */}
            <div className="absolute right-0 top-full mt-2 w-48 bg-neutral-card border border-neutral-border rounded-xl shadow-2xl invisible group-hover:visible transition-all p-2 z-50">
                <button 
                  onClick={logout}
                  className="w-full flex items-center gap-3 px-3 py-2.5 text-sm text-status-critical hover:bg-red-500/10 rounded-lg transition-colors group/logout"
                >
                  <LogOut className="h-4 w-4" />
                  <span className="font-semibold">Sign Out</span>
                </button>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}

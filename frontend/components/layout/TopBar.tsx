"use client";

import { Bell, Search, User, LogOut } from "lucide-react";
import { useAuth } from "@/components/auth/AuthContext";

export default function TopBar() {
  const { user, logout } = useAuth();

  return (
    <header className="sticky top-0 z-30 flex h-20 items-center justify-between border-b border-slate-800 bg-[#0F172A]/80 px-8 backdrop-blur-md shadow-sm">
      <div className="flex items-center gap-6">
        <div className="relative">
          <Search className="absolute left-3.5 top-1/2 h-4.5 w-4.5 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            placeholder="Search documents, reports, etc..."
            className="h-11 w-80 rounded-xl border border-slate-700/50 bg-slate-900/50 pl-11 pr-4 text-sm text-slate-200 placeholder-slate-500 outline-none focus:border-blue-500/50 focus:ring-4 focus:ring-blue-500/10 transition-all shadow-inner"
          />
        </div>
      </div>

      <div className="flex items-center gap-4">
        <button className="relative rounded-xl p-2.5 text-slate-400 hover:bg-slate-800/50 hover:text-white transition-all">
          <Bell className="h-5 w-5" />
          <span className="absolute right-2.5 top-2.5 h-2 w-2 rounded-full bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.5)]" />
        </button>

        <div className="h-8 w-px bg-slate-800 mx-2" />

        <div className="flex items-center gap-4">
          <div className="flex flex-col items-end hidden sm:flex">
             <span className="text-sm font-bold text-white tracking-tight">{user?.displayName || "Analyst User"}</span>
             <span className="text-[10px] text-slate-500 font-bold uppercase tracking-widest leading-none">Vyrenzo Analyst</span>
          </div>

          <div className="group relative">
            <button className="flex items-center gap-2 rounded-xl p-1 text-slate-300 hover:bg-slate-800 transition-all border border-slate-800">
                {user?.photoURL ? (
                    <img src={user.photoURL} alt="Avatar" className="h-9 w-9 rounded-lg border border-slate-700" />
                ) : (
                    <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-500/10 border border-blue-500/20">
                    <User className="h-5 w-5 text-blue-400" />
                    </div>
                )}
            </button>
            
            {/* Simple logout tooltip/menu on hover or click */}
            <div className="absolute right-0 top-full mt-2 w-48 bg-slate-900 border border-slate-800 rounded-xl shadow-2xl invisible group-hover:visible transition-all p-2 z-50">
                <button 
                  onClick={logout}
                  className="w-full flex items-center gap-3 px-3 py-2.5 text-sm text-red-400 hover:bg-red-500/10 rounded-lg transition-colors group/logout"
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

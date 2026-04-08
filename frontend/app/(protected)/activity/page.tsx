"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/components/auth/AuthContext";
import { apiRequest } from "@/lib/api";
import { Activity, Search, Filter, CalendarDays, Coins, Cpu, Users } from "lucide-react";

interface ActivityEntry {
  id: string;
  user_id: string;
  user_email: string;
  user_role_id: number;
  user_role_name: string;
  model: string;
  tokens_in: number;
  tokens_out: number;
  cost_usd: number;
  action: string;
  created_at: string;
}

export default function ActivityPage() {
  const { profile } = useAuth();
  const [entries, setEntries] = useState<ActivityEntry[]>([]);
  const [summary, setSummary] = useState<any>({});
  const [loading, setLoading] = useState(true);

  // Permissions Helper
  const canAccess = (resource: string, type: 'read' | 'write') => {
    if (!profile?.allowed_pages) return false;
    if (profile.allowed_pages.includes("*")) return true;
    return profile.allowed_pages.includes(`${resource}:${type}`);
  };

  // Filters
  const [timeFilter, setTimeFilter] = useState<string>("");
  const [roleFilter, setRoleFilter] = useState<string>("");
  const [searchText, setSearchText] = useState<string>("");

  const fetchActivity = async (isInitial = false) => {
    if (isInitial) setLoading(true);
    try {
      let url = "activity";
      const params = new URLSearchParams();
      if (timeFilter) params.append("time_filter", timeFilter);
      if (roleFilter !== "") params.append("role_id_filter", roleFilter);
      if (searchText) params.append("user_email", searchText);
      
      if (params.toString()) {
        url += `?${params.toString()}`;
      }

      const res = await apiRequest<any>(url, { method: "GET" });
      setEntries(res.entries || []);
      setSummary(res.summary || {});
    } catch (e) {
      console.error(e);
    } finally {
      if (isInitial) setLoading(false);
    }
  };

  useEffect(() => {
    if (profile && canAccess('Activity', 'read')) {
      fetchActivity(true);
      
      // Auto-refresh every 3 seconds for dynamic updates WITHOUT shaking
      const interval = setInterval(() => fetchActivity(false), 3000);
      return () => clearInterval(interval);
    } else if (profile) {
      setLoading(false);
    }
  }, [profile, timeFilter, roleFilter, searchText]);

  if (!loading && !canAccess('Activity', 'read')) {
    return (
      <div className="flex flex-col items-center justify-center p-20 text-center bg-neutral-card/30 rounded-2xl border border-neutral-border animate-in fade-in zoom-in duration-500">
        <Activity className="h-16 w-16 text-status-critical mb-4" />
        <h1 className="text-2xl font-bold text-t-heading mb-2">Access Denied</h1>
        <p className="text-t-muted max-w-sm">Permissions for 'Activity Monitoring' have not been granted for your account. Please contact your Super Admin.</p>
      </div>
    );
  }

  const uniqueRoles = Array.from(new Set(entries.map((e) => e.user_role_name)));

  return (
    <div className="max-w-7xl mx-auto space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="flex flex-col gap-4 md:flex-row md:items-center justify-between border-b border-neutral-border pb-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-t-heading flex items-center gap-3">
            <Activity className="h-8 w-8 text-primary" />
            Platform Activity
          </h1>
          <p className="text-t-muted mt-1">Real-time usage logs, cost tracking, and platform auditing.</p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Search Input */}
          <div className="relative group w-full md:w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-t-muted group-focus-within:text-primary transition-colors" />
            <input 
              type="text"
              placeholder="Search Actor Email..."
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              className="w-full bg-neutral-card/50 border border-neutral-border text-t-body text-xs rounded-xl pl-9 pr-4 py-2 outline-none focus:border-primary/30 focus:ring-1 focus:ring-primary/10 transition-all"
            />
          </div>

          {/* Time Filter - Visible to everyone */}
          <div className="flex bg-neutral-card border border-neutral-border rounded-lg p-1">
            {["", "1d", "7d", "30d"].map((t) => (
              <button
                key={t}
                onClick={() => setTimeFilter(t)}
                className={`px-4 py-1.5 text-xs font-semibold rounded-md transition-all ${
                  timeFilter === t
                    ? "bg-primary/20 text-primary"
                    : "text-t-muted hover:text-t-heading"
                }`}
              >
                {t === "" ? "All Time" : t.toUpperCase()}
              </button>
            ))}
          </div>

          {/* Admin & Super Admin Filters - Role 0/1 always see oversight, or if Activity:write granted */}
          {(profile?.role_id === 0 || profile?.role_id === 1 || canAccess('Activity', 'write')) && (
            <select
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value)}
              className="bg-neutral-card border border-neutral-border text-t-body text-sm rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary/50 outline-none"
            >
              <option value="">All Roles</option>
              <option value="0">Super Admin (0)</option>
              <option value="1">Admin (1)</option>
              <option value="2">Analyst (2)</option>
              <option value="3">Viewer (3)</option>
            </select>
          )}
        </div>
      </div>

      {/* Analytics Summary */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-neutral-card/50 border border-neutral-border p-5 rounded-2xl shadow-sm">
          <div className="flex items-center gap-3 mb-2 text-t-muted uppercase tracking-tighter text-[10px] font-bold">
            <Cpu className="h-4 w-4 text-ai-violet" /> 
            <span>Total Queries</span>
          </div>
          <p className="text-3xl font-bold text-t-heading">{summary.total_queries || 0}</p>
        </div>

        <div className="bg-neutral-card/50 border border-neutral-border p-5 rounded-2xl">
          <div className="flex items-center gap-3 mb-2 text-t-muted">
            <Coins className="h-5 w-5 text-status-medium" /> 
            <span className="text-sm font-semibold">Total Cost</span>
          </div>
          <p className="text-3xl font-bold text-t-heading">${summary.total_cost_usd?.toFixed(4) || "0.0000"}</p>
        </div>
        <div className="bg-neutral-card/50 border border-neutral-border p-5 rounded-2xl">
          <div className="flex items-center gap-3 mb-2 text-t-muted">
            <Activity className="h-5 w-5 text-status-success" /> 
            <span className="text-sm font-semibold">Tokens In</span>
          </div>
          <p className="text-3xl font-bold text-t-heading">{(summary.total_tokens_in || 0).toLocaleString()}</p>
        </div>
        <div className="bg-neutral-card/50 border border-neutral-border p-5 rounded-2xl">
          <div className="flex items-center gap-3 mb-2 text-t-muted">
            <Activity className="h-5 w-5 text-primary" /> 
            <span className="text-sm font-semibold">Tokens Out</span>
          </div>
          <p className="text-3xl font-bold text-t-heading">{(summary.total_tokens_out || 0).toLocaleString()}</p>
        </div>
      </div>

      {/* Data Table */}
          <div className="bg-neutral-card border border-neutral-border rounded-2xl overflow-hidden shadow-sm">
        {loading ? (
          <div className="p-8 text-center text-t-muted animate-pulse">Loading activity logs...</div>
        ) : entries.length === 0 ? (
          <div className="p-8 text-center text-t-muted">No activity logs found for this timeframe.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-neutral-app/50 text-t-muted">
                <tr>
                  <th className="px-6 py-4 font-semibold text-[10px] tracking-wider uppercase whitespace-nowrap">Timestamp</th>
                  <th className="px-6 py-4 font-semibold text-[10px] tracking-wider uppercase whitespace-nowrap">User</th>
                  <th className="px-6 py-4 font-semibold text-[10px] tracking-wider uppercase whitespace-nowrap">Role</th>
                  <th className="px-6 py-4 font-semibold text-[10px] tracking-wider uppercase">Action / Model</th>
                  <th className="px-6 py-4 font-semibold text-[10px] tracking-wider uppercase whitespace-nowrap">Tokens (In/Out)</th>
                  <th className="px-6 py-4 font-semibold text-[10px] tracking-wider uppercase text-right whitespace-nowrap">Cost (USD)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-border">
                {entries.map((entry) => (
                  <tr key={entry.id} className="hover:bg-neutral-row/30 transition-colors">
                    <td className="px-6 py-4">
                      <div className="flex flex-col">
                        <span className="text-t-heading font-medium text-[11px]">
                          {new Date(entry.created_at).toLocaleString('en-IN', {
                            timeZone: 'Asia/Kolkata',
                            day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit", hour12: true
                          })}
                        </span>
                      </div>
                    </td>


                    <td className="px-6 py-4 font-medium text-t-heading text-xs">{entry.user_email}</td>
                    <td className="px-6 py-4">
                        <span className={`px-2 py-1 text-[9px] font-bold uppercase tracking-widest rounded ${
                        entry.user_role_id === 0 ? "bg-status-medium-bg text-status-medium border border-amber-500/20" :
                        entry.user_role_id === 1 ? "bg-ai-violet/10 text-ai-violet border border-indigo-500/20" :
                        "bg-neutral-row text-t-muted"
                        }`}>
                        {entry.user_role_name}
                        </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex flex-col max-w-[280px] md:max-w-md">
                        <span className="text-t-heading text-xs font-bold leading-tight break-all">
                          {entry.action || "Unknown"}
                        </span>
                        <span className="text-[10px] text-t-muted font-mono truncate" title={entry.model}>
                          {entry.model}
                        </span>
                      </div>
                    </td>

                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <span className="text-status-success text-xs bg-status-success-bg px-1.5 py-0.5 rounded">
                          ↑ {entry.tokens_in}
                        </span>
                        <span className="text-primary text-xs bg-primary-subtle px-1.5 py-0.5 rounded">
                          ↓ {entry.tokens_out}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right font-mono text-status-medium">
                      ${entry.cost_usd.toFixed(5)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

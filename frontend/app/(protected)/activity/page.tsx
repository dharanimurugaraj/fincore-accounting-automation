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

  // Filters
  const [timeFilter, setTimeFilter] = useState<string>("");
  const [roleFilter, setRoleFilter] = useState<string>("");

  const fetchActivity = async () => {
    setLoading(true);
    try {
      let url = "activity";
      const params = new URLSearchParams();
      if (timeFilter) params.append("time_filter", timeFilter);
      if (roleFilter !== "") params.append("role_id_filter", roleFilter);
      
      if (params.toString()) {
        url += `?${params.toString()}`;
      }

      const res = await apiRequest<any>(url, { method: "GET" });
      setEntries(res.entries || []);
      setSummary(res.summary || {});
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (profile) {
      fetchActivity();
    }
  }, [profile, timeFilter, roleFilter]);

  const uniqueRoles = Array.from(new Set(entries.map((e) => e.user_role_name)));

  return (
    <div className="max-w-7xl mx-auto space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="flex flex-col gap-4 md:flex-row md:items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-t-heading flex items-center gap-3">
            <Activity className="h-8 w-8 text-primary" />
            Platform Activity
          </h1>
          <p className="text-t-muted mt-1">Real-time usage logs, cost tracking, and platform auditing.</p>
        </div>

        <div className="flex flex-wrap gap-3">
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

          {/* Admin & Super Admin Filters */}
          {(profile?.role_id === 0 || profile?.role_id === 1) && (
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
        <div className="bg-neutral-card/50 border border-neutral-border p-5 rounded-2xl">
          <div className="flex items-center gap-3 mb-2 text-t-muted">
            <Cpu className="h-5 w-5 text-ai-violet" /> 
            <span className="text-sm font-semibold">Total Queries</span>
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
      <div className="bg-neutral-card border border-neutral-border rounded-2xl overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-t-muted animate-pulse">Loading activity logs...</div>
        ) : entries.length === 0 ? (
          <div className="p-8 text-center text-t-muted">No activity logs found for this timeframe.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm whitespace-nowrap">
              <thead className="bg-neutral-app/50 text-t-muted">
                <tr>
                  <th className="px-6 py-4 font-semibold text-xs tracking-wider uppercase">Timestamp</th>
                  {(profile?.role_id === 0 || profile?.role_id === 1) && (
                    <>
                      <th className="px-6 py-4 font-semibold text-xs tracking-wider uppercase">User</th>
                      <th className="px-6 py-4 font-semibold text-xs tracking-wider uppercase">Role</th>
                    </>
                  )}
                  <th className="px-6 py-4 font-semibold text-xs tracking-wider uppercase">Action / Model</th>
                  <th className="px-6 py-4 font-semibold text-xs tracking-wider uppercase">Tokens (In/Out)</th>
                  <th className="px-6 py-4 font-semibold text-xs tracking-wider uppercase text-right">Cost (USD)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-border">
                {entries.map((entry) => (
                  <tr key={entry.id} className="hover:bg-neutral-row/30 transition-colors">
                    <td className="px-6 py-4">
                      <span className="text-t-body">
                        {new Date(entry.created_at).toLocaleString([], {
                          month: "short", day: "numeric", hour: "2-digit", minute: "2-digit"
                        })}
                      </span>
                    </td>
                    {(profile?.role_id === 0 || profile?.role_id === 1) && (
                      <>
                        <td className="px-6 py-4 font-medium text-t-heading">{entry.user_email}</td>
                        <td className="px-6 py-4">
                          <span className={`px-2 py-1 text-[10px] font-bold uppercase tracking-widest rounded ${
                            entry.user_role_id === 0 ? "bg-status-medium-bg text-status-medium border border-amber-500/20" :
                            entry.user_role_id === 1 ? "bg-ai-violet/10 text-ai-violet border border-indigo-500/20" :
                            "bg-neutral-row text-t-muted"
                          }`}>
                            {entry.user_role_name}
                          </span>
                        </td>
                      </>
                    )}
                    <td className="px-6 py-4">
                      <div className="flex flex-col">
                        <span className="text-t-heading capitalize">{entry.action || "Unknown"}</span>
                        <span className="text-xs text-t-muted">{entry.model}</span>
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

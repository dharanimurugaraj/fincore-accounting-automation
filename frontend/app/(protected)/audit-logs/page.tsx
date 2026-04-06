"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/components/auth/AuthContext";
import { apiRequest } from "@/lib/api";
import { ShieldCheck, Search, Filter, CalendarDays, History, Download } from "lucide-react";

interface AuditEntry {
  id: string;
  user_id: string;
  user_email: string;
  user_role_id: number;
  user_role_name: string;
  action: string;
  entity_type: string;
  entity_id: string;
  metadata: string;
  created_at: string;
}

export default function AuditLogsPage() {
  const { profile } = useAuth();
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);

  // Filters
  const [timeFilter, setTimeFilter] = useState<string>("");
  const [roleFilter, setRoleFilter] = useState<string>("");
  const [actionFilter, setActionFilter] = useState<string>("");

  const fetchAuditLogs = async () => {
    setLoading(true);
    try {
      let url = "audit-logs";
      const params = new URLSearchParams();
      if (timeFilter) params.append("time_filter", timeFilter);
      if (roleFilter !== "") params.append("role_id_filter", roleFilter);
      if (actionFilter) params.append("action", actionFilter);
      
      if (params.toString()) {
        url += `?${params.toString()}`;
      }

      const res = await apiRequest<any>(url, { method: "GET" });
      setEntries(res.entries || []);
    } catch (e) {
      console.error("Failed to fetch audit logs:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (profile) {
      fetchAuditLogs();
    }
  }, [profile, timeFilter, roleFilter, actionFilter]);

  const handleExport = async () => {
    try {
        let url = "audit-logs/export";
        const params = new URLSearchParams();
        if (timeFilter) params.append("time_filter", timeFilter);
        
        if (params.toString()) {
          url += `?${params.toString()}`;
        }
        
        const response: any = await apiRequest(url, { method: "GET" });
        // Handling CSV download (assuming backend returns text block natively if text/csv)
        // If apiRequest parses JSON, you might need a direct fetch for the blob here
        const blob = new Blob([response.toString()], { type: 'text/csv' });
        const objUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = objUrl;
        a.download = `audit_logs_${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
    } catch (e) {
        console.error("Export failed:", e);
    }
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="flex flex-col gap-4 md:flex-row md:items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-t-heading flex items-center gap-3">
            <ShieldCheck className="h-8 w-8 text-rose-400" />
            Audit Logs
          </h1>
          <p className="text-t-muted mt-1">Immutable record of system actions, updates, and events.</p>
        </div>

        <div className="flex flex-wrap gap-3">
           {/* Time Filter */}
           <div className="flex bg-neutral-card border border-neutral-border rounded-lg p-1">
            {["", "1d", "7d", "30d"].map((t) => (
              <button
                key={t}
                onClick={() => setTimeFilter(t)}
                className={`px-4 py-1.5 text-xs font-semibold rounded-md transition-all ${
                  timeFilter === t
                    ? "bg-status-critical/20 text-rose-400"
                    : "text-t-muted hover:text-t-heading"
                }`}
              >
                {t === "" ? "All Time" : t.toUpperCase()}
              </button>
            ))}
          </div>

          {/* Admin Filters */}
          {(profile?.role_id === 0 || profile?.role_id === 1) && (
            <>
              <select
                value={roleFilter}
                onChange={(e) => setRoleFilter(e.target.value)}
                className="bg-neutral-card border border-neutral-border text-t-body text-sm rounded-lg px-4 py-2 focus:ring-2 focus:ring-rose-500/50 outline-none"
              >
                <option value="">All Roles</option>
                <option value="0">Super Admin (0)</option>
                <option value="1">Admin (1)</option>
                <option value="2">Analyst (2)</option>
                <option value="3">Viewer (3)</option>
              </select>

              <button 
                onClick={handleExport}
                className="flex items-center gap-2 bg-neutral-row hover:bg-neutral-border text-t-heading text-sm px-4 py-2 rounded-lg font-medium transition-colors"
               >
                 <Download className="w-4 h-4" />
                 Export CSV
              </button>
            </>
          )}
        </div>
      </div>

      <div className="bg-neutral-card border border-neutral-border rounded-2xl overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-t-muted animate-pulse">Loading audit logs...</div>
        ) : entries.length === 0 ? (
          <div className="p-8 text-center text-t-muted">No audit records found for this timeframe.</div>
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
                  <th className="px-6 py-4 font-semibold text-xs tracking-wider uppercase">Action</th>
                  <th className="px-6 py-4 font-semibold text-xs tracking-wider uppercase">Entity Type</th>
                  <th className="px-6 py-4 font-semibold text-xs tracking-wider uppercase">Metadata</th>
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
                      <span className="text-rose-400 font-semibold">{entry.action}</span>
                    </td>
                    <td className="px-6 py-4">
                       <span className="text-t-heading">{entry.entity_type} <span className="text-t-muted text-xs ml-1">({entry.entity_id})</span></span>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-xs text-t-muted font-mono max-w-xs truncate inline-block">
                        {entry.metadata || "-"}
                      </span>
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

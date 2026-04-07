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

  // Prettify Metadata Helper
  const formatMetadata = (entry: AuditEntry) => {
    if (!entry.metadata) return "—";
    try {
      const data = typeof entry.metadata === 'string' ? JSON.parse(entry.metadata) : entry.metadata;
      
      switch(entry.action) {
        case 'UPDATE_USER_ROLE':
          return `Changed ${data.target_email || 'user'} role to ${data.new_role_name || data.new_role}`;
        case 'LIST_CUSTOMERS':
          return `Viewed customer directory (${data.count || 0} results)`;
        case 'CREATE_CUSTOMER':
          return `Added new customer: ${data.company_name}`;
        case 'UPDATE_CUSTOMER':
          return `Updated customer: ${data.company_name}`;
        default:
          return Object.entries(data)
            .map(([k, v]) => `${k.replace(/_/g, ' ')}: ${v}`)
            .join(' | ');
      }
    } catch (e) {
      return typeof entry.metadata === 'string' ? entry.metadata : JSON.stringify(entry.metadata);
    }
  };

  // Status/Action Color Helper
  const getActionStyles = (action: string) => {
    if (action.includes('CREATE')) return 'text-status-success bg-status-success-bg border-status-success/20';
    if (action.includes('UPDATE')) return 'text-ai-violet bg-ai-violet-light border-ai-violet/20';
    if (action.includes('DELETE')) return 'text-status-critical bg-status-critical-bg border-status-critical/20';
    return 'text-t-muted bg-neutral-row border-neutral-border';
  };

  // Filters
  const [timeFilter, setTimeFilter] = useState<string>("");
  const [roleFilter, setRoleFilter] = useState<string>("");
  const [actionFilter, setActionFilter] = useState<string>("");
  const [searchText, setSearchText] = useState<string>("");

  const fetchAuditLogs = async () => {
    setLoading(true);
    try {
      let url = "audit-logs";
      const params = new URLSearchParams();
      if (timeFilter) params.append("time_filter", timeFilter);
      if (roleFilter !== "") params.append("role_id_filter", roleFilter);
      if (actionFilter) params.append("action", actionFilter);
      if (searchText) params.append("user_email", searchText);
      
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
  }, [profile, timeFilter, roleFilter, actionFilter, searchText]);

  const handleExport = async () => {
    try {
        let url = "audit-logs/export";
        const params = new URLSearchParams();
        if (timeFilter) params.append("time_filter", timeFilter);
        
        if (params.toString()) {
          url += `?${params.toString()}`;
        }
        
        const response: any = await apiRequest(url, { method: "GET" });
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
    <div className="max-w-7xl mx-auto space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-700 pb-20">
      <div className="flex flex-col gap-4 md:flex-row md:items-center justify-between border-b border-neutral-border pb-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-t-heading flex items-center gap-3">
            <ShieldCheck className="h-8 w-8 text-status-critical" />
            Audit Logs
          </h1>
          <p className="text-t-muted mt-1">Real-time immutable record of platform operations and administrative actions.</p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
            {/* Search Input */}
            <div className="relative group w-full md:w-64">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-t-muted group-focus-within:text-status-critical transition-colors" />
                <input 
                    type="text"
                    placeholder="Search Actor Email..."
                    value={searchText}
                    onChange={(e) => setSearchText(e.target.value)}
                    className="w-full bg-neutral-card/50 border border-neutral-border text-t-body text-xs rounded-xl pl-9 pr-4 py-2 outline-none focus:border-status-critical/30 focus:ring-1 focus:ring-status-critical/10 transition-all"
                />
            </div>

            <div className="flex bg-neutral-card/50 border border-neutral-border p-1 rounded-xl">
            {["", "1d", "7d", "30d"].map((t) => (
              <button
                key={t}
                onClick={() => setTimeFilter(t)}
                className={`px-3 py-1.5 text-[10px] font-bold uppercase tracking-widest rounded-lg transition-all ${
                  timeFilter === t
                    ? "bg-neutral-border text-t-heading shadow-sm"
                    : "text-t-muted hover:text-t-heading"
                }`}
              >
                {t === "" ? "All Time" : t.toUpperCase()}
              </button>
            ))}
          </div>

          {(profile?.role_id === 0 || profile?.role_id === 1) && (
            <>
              <select
                value={roleFilter}
                onChange={(e) => setRoleFilter(e.target.value)}
                className="bg-neutral-card/50 border border-neutral-border text-t-body text-xs rounded-xl px-3 py-2 outline-none focus:border-neutral-border"
              >
                <option value="">All Roles</option>
                <option value="0">Super Admin (0)</option>
                <option value="1">Admin (1)</option>
                <option value="2">Analyst (2)</option>
                <option value="3">Viewer (3)</option>
              </select>

              <button 
                onClick={handleExport}
                className="flex items-center gap-2 bg-neutral-card/50 border border-neutral-border hover:bg-neutral-border text-t-heading text-xs px-4 py-2 rounded-xl font-bold transition-all"
               >
                 <Download className="w-3.5 h-3.5" />
                 EXPORT
              </button>
            </>
          )}
        </div>
      </div>

      {/* Main Container with Min-Height to prevent shaking/jumping */}
      <div className="bg-neutral-card/30 border border-neutral-border rounded-2xl overflow-hidden backdrop-blur-xl min-h-[500px]">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm border-collapse">
            <thead>
               <tr className="bg-neutral-row/40 border-b border-neutral-border">
                <th className="px-6 py-4 font-bold text-[10px] tracking-widest uppercase text-t-muted">Timestamp (IST)</th>
                <th className="px-6 py-4 font-bold text-[10px] tracking-widest uppercase text-t-muted">Actor Profile</th>
                <th className="px-6 py-4 font-bold text-[10px] tracking-widest uppercase text-t-muted">Operation</th>
                <th className="px-6 py-4 font-bold text-[10px] tracking-widest uppercase text-t-muted">Description</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-border">
              {loading ? (
                Array.from({ length: 8 }).map((_, i) => (
                  <tr key={`skeleton-${i}`} className="animate-pulse">
                    <td className="px-6 py-4"><div className="h-8 w-32 bg-neutral-border/20 rounded-lg" /></td>
                    <td className="px-6 py-4"><div className="h-8 w-40 bg-neutral-border/20 rounded-lg" /></td>
                    <td className="px-6 py-4"><div className="h-6 w-24 bg-neutral-border/20 rounded-md" /></td>
                    <td className="px-6 py-4"><div className="h-8 w-64 bg-neutral-border/20 rounded-lg" /></td>
                  </tr>
                ))
              ) : entries.length === 0 ? (
                <tr>
                  <td colSpan={4} className="p-20 text-center text-t-muted font-medium">No audit records identified within this scope.</td>
                </tr>
              ) : (

                entries.map((entry) => (
                  <tr key={entry.id} className="group hover:bg-neutral-row/30 transition-all duration-300">
                    <td className="px-6 py-4">
                      <div className="flex flex-col">
                        <span className="text-t-heading font-medium text-xs">
                          {new Date(entry.created_at).toLocaleString('en-IN', {
                            timeZone: 'Asia/Kolkata',
                            day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit", hour12: true
                          })}
                        </span>
                        <span className="text-[10px] text-t-muted uppercase font-mono italic opacity-40 group-hover:opacity-100 transition-opacity">
                          ID: {entry.id.substring(0, 8)}
                        </span>
                      </div>
                    </td>

                    <td className="px-6 py-4">
                      <div className="flex flex-col">
                        <span className="text-t-heading font-bold text-xs truncate max-w-[180px]">{entry.user_email}</span>
                        <span className="text-[9px] font-bold tracking-widest text-t-muted uppercase flex items-center gap-1.5 mt-0.5">
                            <span className={`w-1.5 h-1.5 rounded-full ${entry.user_role_id === 0 ? 'bg-amber-400' : 'bg-ai-violet'}`} />
                            {entry.user_role_name}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center rounded-lg border px-2.5 py-1 text-[9px] font-bold uppercase tracking-widest transition-colors ${getActionStyles(entry.action)}`}>
                        {entry.action.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex flex-col">
                        <span className="text-t-heading font-medium text-xs break-words max-w-[300px]">
                           {formatMetadata(entry)}
                        </span>
                        <span className="text-[9px] text-t-muted uppercase font-bold tracking-tighter mt-1">
                          {entry.entity_type} {entry.entity_id.startsWith('user_') || entry.entity_id.startsWith('cust_') ? '' : `(${entry.entity_id})`}
                        </span>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}



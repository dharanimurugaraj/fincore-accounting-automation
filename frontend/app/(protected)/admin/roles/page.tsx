"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/components/auth/AuthContext";
import { apiRequest } from "@/lib/api";
import { Users, ShieldAlert, Check, X } from "lucide-react";

interface RoleEntry {
  id: number;
  name: string;
  description: string;
  allowedPages: string[];
}

const RESOURCES = [
  { id: "Dashboard", label: "Dashboard" },
  { id: "Customers", label: "Customers" },
  { id: "Upload", label: "Upload" },
  { id: "Documents", label: "Documents" },
  { id: "Reports", label: "Reports" },
  { id: "WCDL", label: "WCDL Tracker" },
  { id: "Forex", label: "Forex Register" },
  { id: "Activity", label: "Activity" },
  { id: "Audit", label: "Audit Logs" }
];

export default function RoleManagementPage() {
  const { profile } = useAuth();
  const [roles, setRoles] = useState<RoleEntry[]>([]);
  const [loading, setLoading] = useState(true);

  // Form State
  const [showForm, setShowForm] = useState(false);
  const [roleName, setRoleName] = useState("");
  const [roleDesc, setRoleDesc] = useState("");
  const [selectedPages, setSelectedPages] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);

  const fetchRoles = async () => {
    setLoading(true);
    try {
      const res: any = await apiRequest("admin/roles", { method: "GET" });
      setRoles(res.roles || []);
    } catch (e) {
      console.error("Failed to fetch roles:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (profile?.role_id === 0 || profile?.role_id === 1) {
      fetchRoles();
    }
  }, [profile]);

  const togglePermission = (resourceId: string, type: 'read' | 'write') => {
    const perm = `${resourceId}:${type}`;
    if (selectedPages.includes(perm)) {
      setSelectedPages(selectedPages.filter(p => p !== perm));
    } else {
      setSelectedPages([...selectedPages, perm]);
    }
  };

  const hasPerm = (resourceId: string, type: 'read' | 'write') => {
    return selectedPages.includes(`${resourceId}:${type}`) || selectedPages.includes("*");
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
        await apiRequest("admin/roles", {
            method: "POST",
            body: {
                name: roleName,
                description: roleDesc,
                allowedPages: selectedPages
            }
        });
        setShowForm(false);
        setRoleName("");
        setRoleDesc("");
        setSelectedPages([]);
        fetchRoles();
    } catch (error) {
        console.error("Failed to save role", error);
        alert("Failed to save role. Super admin privileges required.");
    } finally {
        setSaving(false);
    }
  };

  const handleEdit = (r: RoleEntry) => {
    if (r.id === 0 || r.id === 1) {
        alert("System specific roles (SUPER ADMIN, ADMIN) cannot be edited via the UI.");
        return;
    }
    setRoleName(r.name);
    setRoleDesc(r.description || "");
    setSelectedPages(r.allowedPages || []);
    setShowForm(true);
  }

  if (profile?.role_id !== 0 && profile?.role_id !== 1) {
    return (
      <div className="flex flex-col items-center justify-center p-20 text-center">
        <ShieldAlert className="h-16 w-16 text-status-critical mb-4" />
        <h1 className="text-2xl font-bold text-t-heading mb-2">Access Denied</h1>
        <p className="text-t-muted">You must be a system administrator to manage roles.</p>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="flex flex-col gap-4 md:flex-row md:items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-t-heading flex items-center gap-3">
            <Users className="h-8 w-8 text-ai-violet" />
            Role Management
          </h1>
          <p className="text-t-muted mt-1">Create and configure dynamic roles and module access permissions.</p>
        </div>

        {profile?.role_id === 0 && (
            <button
            onClick={() => {
                setRoleName("");
                setRoleDesc("");
                setSelectedPages([]);
                setShowForm(!showForm);
            }}
            className="px-4 py-2 bg-ai-violet hover:bg-ai-violet text-t-heading font-medium rounded-lg transition-colors border border-indigo-500/20"
            >
            {showForm ? "Cancel" : "+ Create Custom Role"}
            </button>
        )}
      </div>

      {showForm && (
        <form onSubmit={handleSave} className="bg-neutral-card border border-neutral-border p-6 rounded-2xl shadow-xl space-y-6">
          <h2 className="text-xl font-semibold text-t-heading">Define Role Details</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2">
                <label className="text-xs font-semibold text-t-muted uppercase tracking-wider">Role Name</label>
                <input 
                  required
                  value={roleName}
                  onChange={(e) => setRoleName(e.target.value)}
                  placeholder="e.g. AUDITOR"
                  className="w-full bg-neutral-app border border-neutral-border rounded-lg px-4 py-3 text-t-heading focus:ring-2 focus:ring-primary/50 outline-none uppercase"
                />
            </div>
            <div className="space-y-2">
                <label className="text-xs font-semibold text-t-muted uppercase tracking-wider">Description</label>
                <input 
                  value={roleDesc}
                  onChange={(e) => setRoleDesc(e.target.value)}
                  placeholder="Optional description of the role's purpose"
                  className="w-full bg-neutral-app border border-neutral-border rounded-lg px-4 py-3 text-t-heading focus:ring-2 focus:ring-primary/50 outline-none"
                />
            </div>
          </div>

          <div className="space-y-4">
             <label className="text-xs font-semibold text-t-muted uppercase tracking-wider block border-b border-neutral-border pb-2">Module Access Configuration</label>
             <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {RESOURCES.map(res => {
                    const read = hasPerm(res.id, 'read');
                    const write = hasPerm(res.id, 'write');
                    
                    return (
                        <div key={res.id} className="p-4 rounded-xl bg-neutral-app border border-neutral-border space-y-3">
                            <h3 className="font-bold text-t-heading text-sm">{res.label}</h3>
                            <div className="flex gap-2">
                                <button
                                    type="button"
                                    onClick={() => togglePermission(res.id, 'read')}
                                    className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-md border text-xs font-bold transition-all ${
                                        read ? "bg-status-success/10 border-emerald-500/50 text-emerald-400" : "bg-neutral-row border-neutral-border text-t-muted"
                                    }`}
                                >
                                    {read ? <Check className="w-3 h-3" /> : <X className="w-3 h-3" />}
                                    VIEW
                                </button>
                                <button
                                    type="button"
                                    onClick={() => togglePermission(res.id, 'write')}
                                    className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-md border text-xs font-bold transition-all ${
                                        write ? "bg-status-critical/10 border-rose-500/50 text-rose-400" : "bg-neutral-row border-neutral-border text-t-muted"
                                    }`}
                                >
                                    {write ? <Check className="w-3 h-3" /> : <X className="w-3 h-3" />}
                                    EDIT
                                </button>
                            </div>
                        </div>
                    )
                })}
             </div>
          </div>

          <div className="flex justify-end border-t border-neutral-border pt-6">
             <button disabled={saving} type="submit" className="px-6 py-2 bg-ai-violet hover:bg-ai-violet disabled:opacity-50 text-t-heading font-medium rounded-lg transition-colors shadow-lg shadow-indigo-500/10">
                {saving ? "Saving..." : "Save Role Configuration"}
             </button>
          </div>
        </form>
      )}

      {/* Existing Roles Table */}
      <div className="bg-neutral-card border border-neutral-border rounded-2xl overflow-hidden shadow-sm">
        {loading ? (
          <div className="p-8 text-center text-t-muted animate-pulse">Loading roles configuration...</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm whitespace-nowrap">
              <thead className="bg-neutral-app/50 text-t-muted">
                <tr>
                  <th className="px-6 py-4 font-semibold text-xs tracking-wider uppercase">ID</th>
                  <th className="px-6 py-4 font-semibold text-xs tracking-wider uppercase">Role Name</th>
                  <th className="px-6 py-4 font-semibold text-xs tracking-wider uppercase">Description</th>
                  <th className="px-6 py-4 font-semibold text-xs tracking-wider uppercase">Assigned Access</th>
                  {profile?.role_id === 0 && <th className="px-6 py-4 font-semibold text-xs tracking-wider uppercase text-right">Actions</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-border">
                {roles.map((r) => (
                  <tr key={r.id} className="hover:bg-neutral-row/30 transition-colors">
                    <td className="px-6 py-4 font-mono text-t-muted text-[11px]">{r.id}</td>
                    <td className="px-6 py-4">
                        <span className={`px-2 py-1 text-[10px] font-bold uppercase tracking-widest rounded inline-block shadow-sm ${
                            r.id === 0 ? "bg-status-medium-bg text-status-medium border border-amber-500/20" :
                            r.id === 1 ? "bg-ai-violet/10 text-ai-violet border border-indigo-500/20" :
                            "bg-neutral-row text-t-body"
                        }`}>
                            {r.name}
                        </span>
                    </td>
                    <td className="px-6 py-4 text-t-muted text-xs">
                        {r.description || "-"}
                    </td>
                    <td className="px-6 py-4">
                        <div className="flex flex-wrap gap-1 max-w-md">
                            {r.allowedPages?.includes("*") ? (
                                <span className="text-status-success text-[9px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-status-success-bg border border-emerald-500/10">Full Platform Access</span>
                            ) : (
                                r.allowedPages?.slice(0, 5).map(p => {
                                    const [mod, access] = p.split(':');
                                    return (
                                        <span key={p} className={`text-[9px] uppercase tracking-tighter px-1.5 py-0.5 rounded border whitespace-nowrap ${
                                            access === 'write' ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' : 'bg-neutral-row text-t-muted border-neutral-border'
                                        }`}>
                                            {mod}{access ? `:${access}` : ''}
                                        </span>
                                    )
                                })
                            )}
                            {(r.allowedPages?.length > 5 && !r.allowedPages.includes("*")) && (
                                <span className="text-t-muted text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-neutral-row/50">+{r.allowedPages.length - 5} MORE</span>
                            )}
                        </div>
                    </td>
                    {profile?.role_id === 0 && (
                        <td className="px-6 py-4 text-right">
                           {r.id > 1 ? (
                               <button onClick={() => handleEdit(r)} className="text-ai-violet hover:text-indigo-300 font-bold text-[10px] uppercase tracking-widest border border-indigo-500/20 px-3 py-1 rounded-md hover:bg-ai-violet/10 transition-all">
                                   Configure
                               </button>
                           ) : (
                               <span className="text-t-muted text-[9px] uppercase tracking-widest cursor-not-allowed opacity-50">System Root</span>
                           )}
                        </td>
                    )}
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


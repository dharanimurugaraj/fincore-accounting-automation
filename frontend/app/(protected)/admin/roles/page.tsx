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

const AVAILABLE_PAGES = [
  "Dashboard",
  "Upload",
  "Documents",
  "Reports",
  "WCDL Tracker",
  "Forex Register",
  "Activity",
  "Audit Logs"
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

  const togglePage = (page: string) => {
    if (selectedPages.includes(page)) {
      setSelectedPages(selectedPages.filter(p => p !== page));
    } else {
      setSelectedPages([...selectedPages, page]);
    }
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
    setSelectedPages(r.allowedPages?.includes("*") ? AVAILABLE_PAGES : (r.allowedPages || []));
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
                setSelectedPages(AVAILABLE_PAGES);
                setShowForm(!showForm);
            }}
            className="px-4 py-2 bg-ai-violet hover:bg-ai-violet text-t-heading font-medium rounded-lg transition-colors"
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
             <label className="text-xs font-semibold text-t-muted uppercase tracking-wider block border-b border-neutral-border pb-2">Allowed UI Modules</label>
             <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {AVAILABLE_PAGES.map(page => {
                    const isSelected = selectedPages.includes(page);
                    return (
                        <button
                          type="button"
                          onClick={() => togglePage(page)}
                          key={page}
                          className={`flex items-center gap-3 p-3 rounded-lg border text-left transition-all ${
                              isSelected ? "bg-ai-violet/10 border-indigo-500/50 text-indigo-300" : "bg-neutral-app border-neutral-border hover:border-neutral-border text-t-muted"
                          }`}
                        >
                            <div className={`w-5 h-5 rounded flex items-center justify-center border ${isSelected ? 'bg-ai-violet border-indigo-500' : 'border-neutral-border'}`}>
                                {isSelected && <Check className="w-3 h-3 text-t-heading" />}
                            </div>
                            <span className="text-sm font-medium">{page}</span>
                        </button>
                    )
                })}
             </div>
          </div>

          <div className="flex justify-end border-t border-neutral-border pt-6">
             <button disabled={saving} type="submit" className="px-6 py-2 bg-ai-violet hover:bg-ai-violet disabled:opacity-50 text-t-heading font-medium rounded-lg transition-colors">
                {saving ? "Saving..." : "Save Role Configuration"}
             </button>
          </div>
        </form>
      )}

      {/* Existing Roles Table */}
      <div className="bg-neutral-card border border-neutral-border rounded-2xl overflow-hidden">
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
                    <td className="px-6 py-4 font-mono text-t-muted">{r.id}</td>
                    <td className="px-6 py-4">
                        <span className={`px-2 py-1 text-[10px] font-bold uppercase tracking-widest rounded inline-block ${
                            r.id === 0 ? "bg-status-medium-bg text-status-medium border border-amber-500/20" :
                            r.id === 1 ? "bg-ai-violet/10 text-ai-violet border border-indigo-500/20" :
                            "bg-neutral-row text-t-body"
                        }`}>
                            {r.name}
                        </span>
                    </td>
                    <td className="px-6 py-4 text-t-muted">
                        {r.description || "-"}
                    </td>
                    <td className="px-6 py-4">
                        <div className="flex flex-wrap gap-1 max-w-md">
                            {r.allowedPages?.includes("*") ? (
                                <span className="text-status-success text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-status-success-bg">Full Platform Access</span>
                            ) : (
                                r.allowedPages?.slice(0, 3).map(p => (
                                    <span key={p} className="text-t-body text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-neutral-row">{p}</span>
                                ))
                            )}
                            {(r.allowedPages?.length > 3 && !r.allowedPages.includes("*")) && (
                                <span className="text-t-muted text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-neutral-row/50">+{r.allowedPages.length - 3} MORE</span>
                            )}
                        </div>
                    </td>
                    {profile?.role_id === 0 && (
                        <td className="px-6 py-4 text-right">
                           {r.id > 1 ? (
                               <button onClick={() => handleEdit(r)} className="text-ai-violet hover:text-indigo-300 font-medium text-xs uppercase tracking-wider">
                                   Edit
                               </button>
                           ) : (
                               <span className="text-t-muted text-[10px] uppercase tracking-widest cursor-not-allowed">System Protected</span>
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

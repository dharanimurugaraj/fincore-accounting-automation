"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/components/auth/AuthContext";
import { apiRequest } from "@/lib/api";
import { UserCog, ShieldAlert, Check } from "lucide-react";

interface SystemUser {
  id: string;
  email: string;
  name: string;
  role_id: number;
  role_name: string;
  last_login: string;
  created_at: string;
}

interface RoleOption {
  id: number;
  name: string;
}

export default function UserManagementPage() {
  const { profile } = useAuth();
  const [users, setUsers] = useState<SystemUser[]>([]);
  const [roles, setRoles] = useState<RoleOption[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [usersRes, rolesRes]: any = await Promise.all([
        apiRequest("admin/users", { method: "GET" }),
        apiRequest("admin/roles", { method: "GET" })
      ]);
      setUsers(usersRes.users || []);
      setRoles((rolesRes.roles || []).map((r: any) => ({ id: r.id, name: r.name })));
    } catch (e) {
      console.error("Failed to fetch users or roles", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (profile?.role_id === 0 || profile?.role_id === 1) {
      fetchData();
    }
  }, [profile]);

  const handleRoleChange = async (userId: string, newRoleId: number) => {
    try {
      await apiRequest(`admin/users/${userId}/role`, {
        method: "PATCH",
        body: { role_id: newRoleId }
      });
      // Optionally reflect update natively to save a network call:
      setUsers(users.map(u => {
          if (u.id === userId) {
              return { ...u, role_id: newRoleId, role_name: roles.find(r => r.id === newRoleId)?.name || "UNKNOWN" };
          }
          return u;
      }));
    } catch (e: any) {
      console.error(e);
      alert("Failed to update user role. " + (e.message || "Insufficient permissions."));
    }
  };

  if (profile?.role_id !== 0 && profile?.role_id !== 1) {
    return (
      <div className="flex flex-col items-center justify-center p-20 text-center">
        <ShieldAlert className="h-16 w-16 text-rose-500 mb-4" />
        <h1 className="text-2xl font-bold text-white mb-2">Access Denied</h1>
        <p className="text-slate-400">You must be an administrator to assign organizational roles.</p>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-3">
          <UserCog className="h-8 w-8 text-emerald-400" />
          User Management
        </h1>
        <p className="text-slate-400 mt-1">Review active users and configure organizational access tiers across the platform.</p>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
        {loading ? (
          <div className="p-12 text-center text-slate-400 animate-pulse font-medium">Loading organization users...</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm whitespace-nowrap">
              <thead className="bg-slate-950/50 text-slate-400">
                <tr>
                  <th className="px-6 py-4 font-semibold text-xs tracking-wider uppercase">User Details</th>
                  <th className="px-6 py-4 font-semibold text-xs tracking-wider uppercase">Last Login</th>
                  <th className="px-6 py-4 font-semibold text-xs tracking-wider uppercase">Status</th>
                  <th className="px-6 py-4 font-semibold text-xs tracking-wider uppercase">Platform Role Target</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50">
                {users.map((u) => (
                  <tr key={u.id} className="hover:bg-slate-800/30 transition-colors group">
                    <td className="px-6 py-4">
                        <div className="flex flex-col">
                            <span className="text-slate-200 font-medium">{u.name || "Unknown Identity"}</span>
                            <span className="text-xs text-slate-500">{u.email}</span>
                        </div>
                    </td>
                    <td className="px-6 py-4 text-slate-400">
                        {u.last_login ? new Date(u.last_login).toLocaleDateString() : 'Never'}
                    </td>
                    <td className="px-6 py-4">
                        <span className="px-2 py-1 text-[10px] font-bold uppercase tracking-widest rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                            Active
                        </span>
                    </td>
                    <td className="px-6 py-4">
                        {/* Protect Admins from tweaking SuperAdmins */}
                        {(profile?.role_id === 1 && u.role_id <= 1) ? (
                            <span className="px-3 py-1.5 text-xs font-bold uppercase text-slate-500 cursor-not-allowed">
                                {u.role_name} (LOCKED)
                            </span>
                        ) : (
                            <select
                                value={u.role_id}
                                onChange={(e) => handleRoleChange(u.id, parseInt(e.target.value))}
                                className={`text-xs font-bold uppercase tracking-widest px-3 py-1.5 rounded outline-none transition-all cursor-pointer ${
                                    u.role_id === 0 ? "bg-amber-500/10 text-amber-400 border border-amber-500/20" :
                                    u.role_id === 1 ? "bg-indigo-500/10 text-indigo-400 border border-indigo-500/20" :
                                    "bg-slate-950 border border-slate-700 text-slate-300 hover:border-slate-500 focus:ring-2 focus:ring-emerald-500/50"
                                }`}
                            >
                                {roles.map(r => (
                                    <option 
                                        key={r.id} 
                                        value={r.id} 
                                        disabled={profile?.role_id === 1 && r.id <= 1} // Admins cannot promote to admin
                                        className="bg-slate-900 text-slate-300"
                                    >
                                        {r.id === 0 ? "★ " : ""}{r.name}
                                    </option>
                                ))}
                            </select>
                        )}
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

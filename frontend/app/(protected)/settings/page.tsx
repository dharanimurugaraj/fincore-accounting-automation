"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/components/auth/AuthContext";
import { apiRequest } from "@/lib/api";
import { Settings, User, Sliders, Bell, Shield, Building, Globe, Loader2, LogOut } from "lucide-react";

export default function SettingsPage() {
  const { profile } = useAuth();
  const [activeTab, setActiveTab] = useState("profile");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // States
  const [profileData, setProfileData] = useState<any>({});
  const [orgData, setOrgData] = useState<any>({});
  const [platformData, setPlatformData] = useState<any>({});

  useEffect(() => {
    const fetchSettings = async () => {
      setLoading(true);
      try {
        const [profRes]: any = await Promise.all([
            apiRequest("settings/profile", { method: "GET" })
        ]);
        setProfileData(profRes.profile || {});

        if (profile?.role_id !== undefined && profile.role_id <= 1) {
            const orgRes: any = await apiRequest("settings/organization", { method: "GET" });
            setOrgData(orgRes.organization || {});
        }

        if (profile?.role_id === 0) {
            const platRes: any = await apiRequest("settings/platform", { method: "GET" });
            setPlatformData(platRes.platform || {});
        }
      } catch (e) {
        console.error("Failed to load settings:", e);
      } finally {
        setLoading(false);
      }
    };

    if (profile) fetchSettings();
  }, [profile]);

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
        await apiRequest("settings/profile", {
            method: "PATCH",
            body: {
                title: profileData.title,
                phone: profileData.phone,
                theme: profileData.theme,
                timezone: profileData.timezone,
            }
        });
        alert("Personal Settings updated successfully.");
    } catch (error) {
        alert("Failed to update settings.");
    } finally {
        setSaving(false);
    }
  };

  const handleSaveOrg = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
        await apiRequest("settings/organization", {
            method: "PATCH",
            body: {
                legalName: orgData.legalName,
                address: orgData.address,
            }
        });
        alert("Organization details updated successfully.");
    } catch (error) {
        alert("Failed to update organization.");
    } finally {
        setSaving(false);
    }
  };

  const tabs = [
    { id: "profile", label: "My Profile", icon: User, allowed: true },
    { id: "preferences", label: "Preferences", icon: Sliders, allowed: true },
    { id: "notifications", label: "Notifications", icon: Bell, allowed: true },
    { id: "security", label: "Security", icon: Shield, allowed: true },
    { id: "organization", label: "Organization Profile", icon: Building, allowed: profile?.role_id !== undefined && profile.role_id <= 1 },
    { id: "platform", label: "Platform Variables", icon: Globe, allowed: profile?.role_id === 0 },
  ];

  if (loading) return <div className="flex justify-center p-20"><Loader2 className="w-8 h-8 animate-spin text-slate-500" /></div>;

  return (
    <div className="max-w-7xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-3">
          <Settings className="h-8 w-8 text-cyan-400" />
          Settings
        </h1>
        <p className="text-slate-400 mt-1">Manage your account settings, configurations, and administrative parameters.</p>
      </div>

      <div className="flex flex-col md:flex-row gap-8">
        {/* Sidebar Nav */}
        <div className="w-full md:w-64 flex-shrink-0">
           <nav className="space-y-1">
               {tabs.filter(t => t.allowed).map(tab => {
                   const isActive = activeTab === tab.id;
                   return (
                       <button
                         key={tab.id}
                         onClick={() => setActiveTab(tab.id)}
                         className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all ${
                             isActive 
                             ? "bg-cyan-500/10 text-cyan-400" 
                             : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
                         }`}
                       >
                           <tab.icon className="w-5 h-5 shrink-0" />
                           {tab.label}
                       </button>
                   )
               })}
           </nav>
        </div>

        {/* Content Area */}
        <div className="flex-1">
           <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl min-h-[400px]">
               {/* -------------------- PROFILE TAB -------------------- */}
               {activeTab === "profile" && (
                   <form onSubmit={handleSaveProfile} className="space-y-6">
                       <h2 className="text-xl font-bold text-white border-b border-slate-800 pb-4">Personal Details</h2>
                       <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                           <div className="space-y-2">
                               <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Email Address</label>
                               <input value={profileData.email || ""} disabled readOnly className="w-full bg-slate-950/50 border border-slate-800 rounded-lg px-4 py-3 text-slate-500 cursor-not-allowed" />
                               <p className="text-[10px] text-slate-500">Email is enforced securely via Auth Provider.</p>
                           </div>
                           <div className="space-y-2">
                               <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Full Name</label>
                               <input disabled readOnly value={profileData.name || ""} className="w-full bg-slate-950/50 border border-slate-800 rounded-lg px-4 py-3 text-slate-500 cursor-not-allowed" />
                           </div>
                           <div className="space-y-2">
                               <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Job Title</label>
                               <input 
                                 value={profileData.title || ""} 
                                 onChange={e => setProfileData({...profileData, title: e.target.value})}
                                 placeholder="e.g. Senior Credit Analyst" 
                                 className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-3 text-white outline-none focus:border-cyan-500/50" />
                           </div>
                           <div className="space-y-2">
                               <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Phone Number</label>
                               <input 
                                 value={profileData.phone || ""} 
                                 onChange={e => setProfileData({...profileData, phone: e.target.value})}
                                 placeholder="+1 (555) 000-0000" 
                                 className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-3 text-white outline-none focus:border-cyan-500/50" />
                           </div>
                       </div>
                       <div className="pt-4 flex justify-end">
                           <button type="submit" disabled={saving} className="px-6 py-2 bg-cyan-600 hover:bg-cyan-500 text-white font-medium rounded-lg">{saving ? "Saving..." : "Save Profile"}</button>
                       </div>
                   </form>
               )}

               {/* -------------------- PREFERENCES TAB -------------------- */}
               {activeTab === "preferences" && (
                   <form onSubmit={handleSaveProfile} className="space-y-6">
                       <h2 className="text-xl font-bold text-white border-b border-slate-800 pb-4">Application Preferences</h2>
                       <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                           <div className="space-y-2">
                               <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Interface Theme</label>
                               <select 
                                 value={profileData.theme || "dark"}
                                 onChange={e => setProfileData({...profileData, theme: e.target.value})}
                                 className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-3 text-white outline-none focus:border-cyan-500/50"
                               >
                                   <option value="dark">Dark Mode (Default)</option>
                                   <option value="light">Light Mode</option>
                                   <option value="system">Sync with System</option>
                               </select>
                           </div>
                           <div className="space-y-2">
                               <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Local Timezone</label>
                               <select 
                                 value={profileData.timezone || "UTC"}
                                 onChange={e => setProfileData({...profileData, timezone: e.target.value})}
                                 className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-3 text-white outline-none focus:border-cyan-500/50"
                               >
                                   <option value="UTC">UTC (Universal)</option>
                                   <option value="EST">Eastern Time (EST)</option>
                                   <option value="GMT">Greenwich Mean Time (GMT)</option>
                                   <option value="IST">India Standard Time (IST)</option>
                               </select>
                           </div>
                       </div>
                       <div className="pt-4 flex justify-end">
                           <button type="submit" disabled={saving} className="px-6 py-2 bg-cyan-600 hover:bg-cyan-500 text-white font-medium rounded-lg">Save Preferences</button>
                       </div>
                   </form>
               )}

               {/* -------------------- ORGANIZATION TAB (ADMIN) -------------------- */}
               {activeTab === "organization" && profile?.role_id !== undefined && profile.role_id <= 1 && (
                   <form onSubmit={handleSaveOrg} className="space-y-6">
                       <h2 className="text-xl font-bold text-indigo-400 border-b border-slate-800 pb-4">Organization configuration</h2>
                       <div className="grid grid-cols-1 gap-6">
                           <div className="space-y-2">
                               <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Legal Entity Name</label>
                               <input 
                                 value={orgData.legalName || ""} 
                                 onChange={e => setOrgData({ ...orgData, legalName: e.target.value })}
                                 placeholder="e.g. Vyrenzo Bank Inc." 
                                 className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-3 text-white outline-none focus:border-indigo-500/50" 
                               />
                           </div>
                           <div className="space-y-2">
                               <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Corporate Address</label>
                               <textarea 
                                 value={orgData.address || ""} 
                                 onChange={e => setOrgData({ ...orgData, address: e.target.value })}
                                 placeholder="123 Bank St..." 
                                 rows={3} 
                                 className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-3 text-white outline-none focus:border-indigo-500/50" 
                               />
                           </div>
                       </div>
                       <div className="pt-4 flex justify-end">
                           <button type="submit" disabled={saving} className="px-6 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-lg">{saving ? "Updating..." : "Update Organization"}</button>
                       </div>
                   </form>
               )}

               {/* -------------------- SECURITY TAB -------------------- */}
               {activeTab === "security" && (
                   <div className="space-y-6">
                       <h2 className="text-xl font-bold text-white border-b border-slate-800 pb-4">Security & Sessions</h2>
                       <div className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-xl flex items-start justify-between">
                           <div>
                               <h3 className="text-rose-400 font-bold">Terminate Sessions</h3>
                               <p className="text-sm text-slate-400 mt-1">Sign out manually out of all web and mobile instances linked to your identity.</p>
                           </div>
                           <button onClick={() => { import("@/lib/firebase").then(({ auth }) => auth.signOut()); }} className="flex items-center gap-2 bg-rose-500 hover:bg-rose-600 px-4 py-2 text-white text-sm font-bold rounded-lg transition-colors">
                               <LogOut className="w-4 h-4" /> Global Sign Out
                           </button>
                       </div>
                   </div>
               )}

               {/* Placeholders for notifications/platform */}
               {activeTab === "notifications" && <div className="text-slate-400 italic text-center p-12">Email alerts infrastructure is currently bypassed in Dev environments.</div>}
               {activeTab === "platform" && <div className="text-slate-400 italic text-center p-12 border border-dashed border-slate-800 bg-slate-950/50 rounded-xl mt-4">Global Constants rendering module... Edit GlobalConfig Table for immediate metrics updates.</div>}
           </div>
        </div>
      </div>
    </div>
  );
}

"use client";

import { useState, useEffect } from "react";
import { 
  FileText, 
  Download, 
  Search, 
  RefreshCw, 
  Calendar, 
  ChevronRight, 
  ShieldCheck,
  AlertCircle,
  Clock
} from "lucide-react";
import { format } from "date-fns";
import { motion } from "framer-motion";
import { api } from "@/lib/api";

// --- Types ---
type RunStatus = 
  | "PENDING" 
  | "STAGE1_RUNNING" 
  | "STAGE1_REVIEW" 
  | "STAGE2_RUNNING" 
  | "STAGE3_RUNNING" 
  | "VALIDATION_FAILED" 
  | "AWAITING_APPROVAL" 
  | "APPROVED" 
  | "FAILED";

interface PipelineRun {
  id: string;
  statementMonth: string;
  status: RunStatus;
  stage: number;
  org_folder: string;
  run_timestamp: string;
  user_email?: string;
  validationResult?: string;
  errorMessage?: string;
  startedAt?: string;
  completedAt?: string;
  createdAt: string;
  workingSheetKey?: string;
  bankingReportKey?: string;
  uploads: Array<{ id: string; filename: string; s3Key: string; status: string; uploaded_by?: string }>;
}

const STATUS_CONFIG: Record<RunStatus, { label: string; bg: string; text: string }> = {
  PENDING: { label: "Pending", bg: "bg-slate-500/10", text: "text-slate-400" },
  STAGE1_RUNNING: { label: "Analyzing", bg: "bg-blue-500/10", text: "text-blue-400" },
  STAGE1_REVIEW: { label: "Quality Review", bg: "bg-amber-500/10", text: "text-amber-400" },
  STAGE2_RUNNING: { label: "Processing", bg: "bg-indigo-500/10", text: "text-indigo-400" },
  STAGE3_RUNNING: { label: "Finalizing", bg: "bg-cyan-500/10", text: "text-cyan-400" },
  VALIDATION_FAILED: { label: "Data Error", bg: "bg-red-500/10", text: "text-red-400" },
  AWAITING_APPROVAL: { label: "Verified", bg: "bg-amber-500/10", text: "text-amber-400" },
  APPROVED: { label: "Audit Ready", bg: "bg-emerald-500/10", text: "text-emerald-400" },
  FAILED: { label: "Aborted", bg: "bg-red-600/10", text: "text-red-500" },
};

export default function DocumentsPage() {
  const [runs, setRuns] = useState<PipelineRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  const fetchRuns = async () => {
    setLoading(true);
    setAuthError(false);
    try {
      const data = await api.get<{ runs: any[] }>(`runs`);
      if (data && data.runs) {
        setRuns(data.runs);
      }
    } catch (err: any) {
      console.error("Failed to fetch pipeline runs:", err);
      if (err.message?.includes("authenticated") || err.message?.includes("401") || err.message?.includes("403")) {
          setAuthError(true);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRuns();
  }, []);

  const handleDownload = (key: string) => {
    const token = localStorage.getItem("fincore_token");
    const downloadUrl = `/api/documents?action=download&key=${encodeURIComponent(key)}&token=${token}`;
    window.open(downloadUrl, "_blank");
  };

  const getValidationBadge = (resultStr?: string) => {
    if (!resultStr) return null;
    try {
      const res = JSON.parse(resultStr);
      const status = res.status?.toUpperCase() || "PASS";
      if (status === "PASS") return <span className="text-[9px] font-black text-emerald-500 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20 uppercase tracking-tight">AI Pass</span>;
      if (status === "WARN") return <span className="text-[9px] font-black text-amber-500 bg-amber-500/10 px-1.5 py-0.5 rounded border border-amber-500/20 uppercase tracking-tight">AI Check</span>;
      return <span className="text-[9px] font-black text-red-500 bg-red-500/10 px-1.5 py-0.5 rounded border border-red-500/20 uppercase tracking-tight">AI Fail</span>;
    } catch {
      return null;
    }
  };

  const formatRunDate = (timestamp: string) => {
    if (!timestamp || timestamp.length < 15) return "Unknown Date";
    try {
      const year = timestamp.substring(0, 4);
      const month = timestamp.substring(4, 6);
      const day = timestamp.substring(6, 8);
      const hour = timestamp.substring(9, 11);
      const min = timestamp.substring(11, 13);
      const date = new Date(`${year}-${month}-${day}T${hour}:${min}:00Z`);
      return format(date, "dd MMM yyyy HH:mm");
    } catch {
      return timestamp;
    }
  };

  const groupedRuns = runs.reduce((acc, run) => {
    const org = run.org_folder || "Global Volume";
    if (!acc[org]) acc[org] = [];
    acc[org].push(run);
    return acc;
  }, {} as Record<string, PipelineRun[]>);

  const filteredOrgs = Object.keys(groupedRuns).filter(org => 
    org.toLowerCase().includes(searchQuery.toLowerCase()) ||
    groupedRuns[org].some(r => r.statementMonth.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  if (authError) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-[#F8FAFC] p-8">
            <div className="w-full max-w-md rounded-[2.5rem] bg-white p-10 text-center shadow-2xl border border-slate-100">
                <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-[1.5rem] bg-red-50 text-4xl">🔐</div>
                <h2 className="mt-8 text-2xl font-black text-[#0D1B3E] italic uppercase tracking-tighter">Access Revoked</h2>
                <p className="mt-3 text-slate-500 font-medium">Your enterprise session identity has expired. Security protocols require a fresh login.</p>
                <button 
                  onClick={() => window.location.reload()}
                  className="mt-10 w-full rounded-2xl bg-[#0ABFBC] py-5 font-black uppercase tracking-[0.2em] text-white shadow-xl shadow-[#0ABFBC]/20 hover:brightness-110 active:scale-[0.98] transition-all text-xs"
                >Re-Authenticate System</button>
            </div>
        </div>
      )
  }

  return (
    <div className="min-h-screen bg-[#F8FAFC] p-8 text-slate-900 font-medium">
      <div className="mx-auto max-w-6xl space-y-10">
        
        {/* Header */}
        <div className="flex items-end justify-between border-b border-slate-200 pb-10">
          <div>
            <div className="flex items-center gap-3 mb-2">
                <div className="h-6 w-1 bg-[#0ABFBC] rounded-full"></div>
                <span className="text-[10px] font-black uppercase tracking-[0.3em] text-[#0ABFBC]">Financial Intelligence Audit</span>
            </div>
            <h1 className="text-4xl font-black text-[#0D1B3E] italic uppercase tracking-tighter">Enterprise Storage Hub</h1>
            <p className="mt-2 text-slate-400 font-bold text-sm">Scalable R2-cloud infrastructure for multi-bank intelligence and audit-ready data.</p>
          </div>
          <button 
            onClick={fetchRuns}
            className="group flex items-center gap-2 rounded-2xl bg-[#0D1B3E] px-6 py-3 text-xs font-black uppercase tracking-widest text-white shadow-xl shadow-[#0D1B3E]/20 transition-all hover:brightness-125 hover:-translate-y-0.5"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh Assets
          </button>
        </div>

        {/* Search */}
        <div className="relative group">
          <Search className="absolute left-6 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-300 group-focus-within:text-[#0ABFBC] transition-colors" />
          <input 
            type="text" 
            placeholder="Search by Volume, Month, or Identity Tag..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="h-16 w-full rounded-[1.5rem] border-none bg-white pl-16 pr-6 shadow-xl shadow-slate-200/50 outline-none ring-1 ring-slate-100 focus:ring-2 focus:ring-[#0ABFBC]/30 transition-all text-slate-700 font-bold italic placeholder:text-slate-200 placeholder:italic"
          />
        </div>

        {/* Directory View */}
        <div className="space-y-16 pb-20">
          {loading && runs.length === 0 ? (
            <div className="flex h-64 flex-col items-center justify-center rounded-[3rem] bg-white shadow-lg border border-slate-50">
              <div className="h-2 w-32 bg-slate-100 rounded-full overflow-hidden">
                  <motion.div 
                    initial={{ width: 0 }}
                    animate={{ width: "100%" }}
                    transition={{ repeat: Infinity, duration: 1.5 }}
                    className="h-full bg-[#0ABFBC]"
                  />
              </div>
              <p className="mt-4 text-[10px] font-black uppercase tracking-widest text-slate-400">Scanning Volumes...</p>
            </div>
          ) : filteredOrgs.length === 0 ? (
            <div className="flex h-64 flex-col items-center justify-center rounded-[3rem] bg-white shadow-xl border border-dashed border-slate-200">
              <FileText className="h-12 w-12 text-slate-100" />
              <p className="mt-4 text-xs font-black uppercase tracking-widest text-slate-300">No matching assets found on cloud.</p>
            </div>
          ) : (
            filteredOrgs.map(org => (
              <div key={org} className="space-y-8">
                <div className="flex items-center gap-5 px-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#0D1B3E] text-white shadow-xl shadow-[#0D1B3E]/30">
                    <ShieldCheck className="h-6 w-6" />
                  </div>
                  <div>
                    <h2 className="text-2xl font-black text-[#0D1B3E] uppercase tracking-tighter italic">{org}</h2>
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Isolated Storage Volume</span>
                  </div>
                  <div className="h-px flex-1 bg-gradient-to-r from-slate-200 to-transparent"></div>
                </div>

                <div className="grid gap-10">
                  {groupedRuns[org].map(run => (
                    <div 
                      key={run.id}
                      className="overflow-hidden rounded-[3.5rem] bg-white border border-slate-100 shadow-2xl shadow-slate-200/40 transition-all hover:scale-[1.005]"
                    >
                      {/* Folder Header */}
                      <div className="flex items-center justify-between bg-slate-50/70 px-10 py-8 border-b border-slate-100">
                        <div className="flex items-center gap-6">
                           <div className="flex h-16 w-16 items-center justify-center rounded-[1.5rem] bg-white shadow-xl shadow-slate-200/50 text-3xl border border-slate-50">📁</div>
                           <div>
                              <div className="flex items-center gap-3 mb-1">
                                <span className="font-black text-[#0D1B3E] italic tracking-tighter text-lg">{run.run_timestamp}</span>
                                <span className="text-[9px] font-black uppercase text-slate-400 bg-white border border-slate-200 rounded-md px-2 py-0.5 shadow-sm">UID: {run.id}</span>
                              </div>
                              <div className="flex items-center gap-3 text-[11px] text-slate-500 font-bold">
                                <span>{formatRunDate(run.run_timestamp)}</span>
                                <span className="h-1 w-1 rounded-full bg-slate-300"></span>
                                <span className="text-[#0ABFBC] uppercase tracking-wide">{run.statementMonth}</span>
                                {run.user_email && (
                                    <>
                                        <span className="h-1 w-1 rounded-full bg-slate-300"></span>
                                        <span className="flex items-center gap-1.5 text-slate-400">
                                            <div className="w-1.5 h-1.5 rounded-full bg-slate-200"></div>
                                            {run.user_email}
                                        </span>
                                    </>
                                )}
                              </div>
                           </div>
                        </div>
                        <div className="flex items-center gap-4">
                           {getValidationBadge(run.validationResult)}
                           <span className={`rounded-xl px-5 py-2 text-[10px] font-black uppercase tracking-[0.2em] shadow-sm ${STATUS_CONFIG[run.status]?.bg} ${STATUS_CONFIG[run.status]?.text}`}>
                             {STATUS_CONFIG[run.status]?.label}
                           </span>
                        </div>
                      </div>

                      {/* File Contents */}
                      <div className="p-10 grid grid-cols-1 md:grid-cols-2 gap-12">
                        
                        {/* Sub-directory: Input Statements */}
                        <div className="space-y-6">
                           <div className="flex items-center justify-between px-2">
                              <span className="text-[10px] font-black text-slate-300 uppercase tracking-[0.3em]">/audit_source_files</span>
                              <span className="h-px flex-1 mx-4 bg-slate-100"></span>
                           </div>
                           <div className="space-y-3">
                              {run.uploads && run.uploads.length > 0 ? (
                                run.uploads.map(up => (
                                  <div key={up.id} className="group flex items-center justify-between rounded-[2rem] border border-slate-200 bg-white p-4 transition-all hover:border-[#0ABFBC]/50 hover:shadow-lg hover:shadow-[#0ABFBC]/5">
                                    <div className="flex items-center gap-4">
                                      <div className="w-10 h-10 bg-slate-50 rounded-2xl flex items-center justify-center text-xl shadow-inner group-hover:bg-[#0ABFBC]/5 transition-colors">📄</div>
                                      <div>
                                          <div className="text-xs font-black text-slate-700 truncate max-w-[200px] italic">{up.filename}</div>
                                          <div className="text-[9px] text-slate-400 font-bold uppercase tracking-widest mt-0.5">Uploaded: {up.uploaded_by || 'Unknown Identity'}</div>
                                      </div>
                                    </div>
                                    <button 
                                      onClick={() => handleDownload(up.s3Key)}
                                      className="rounded-xl p-3 text-slate-300 hover:bg-slate-900 hover:text-white shadow-sm transition-all active:scale-90"
                                    >
                                      <Download className="h-4 w-4" />
                                    </button>
                                  </div>
                                ))
                              ) : (
                                <div className="text-center p-12 rounded-[2rem] bg-slate-50/50 border border-dashed border-slate-200">
                                   <div className="text-xl opacity-30">📭</div>
                                   <p className="text-[10px] font-black text-slate-300 uppercase tracking-widest mt-2">No trace files linked</p>
                                </div>
                              )}
                           </div>
                        </div>

                        {/* Sub-directory: Intelligence Reports */}
                        <div className="space-y-6">
                           <div className="flex items-center justify-between px-2">
                              <span className="text-[10px] font-black text-[#0ABFBC] uppercase tracking-[0.3em]">/intelligence_outputs</span>
                              <span className="h-px flex-1 mx-4 bg-[#0ABFBC]/10"></span>
                           </div>
                           <div className="space-y-4">
                              {run.status === 'APPROVED' ? (
                                <>
                                   {run.workingSheetKey && (
                                     <div className="group flex items-center justify-between rounded-[2rem] border border-[#0D1B3E]/10 bg-[#0D1B3E]/5 p-5 transition-all hover:shadow-2xl hover:shadow-[#0D1B3E]/10 hover:-translate-y-1">
                                      <div className="flex items-center gap-5">
                                        <div className="w-12 h-12 rounded-2xl bg-white shadow-xl shadow-slate-200/50 flex items-center justify-center text-2xl group-hover:scale-110 transition-transform">📊</div>
                                        <div>
                                            <div className="text-sm font-black text-[#0D1B3E] italic uppercase tracking-tighter">Analyzed Working Sheet</div>
                                            <div className="text-[10px] text-slate-400 font-bold tracking-widest">Excel Audit Engine</div>
                                        </div>
                                      </div>
                                      <button 
                                        onClick={() => handleDownload(run.workingSheetKey!)}
                                        className="rounded-2xl bg-[#0D1B3E] px-6 py-3 text-[10px] font-black text-white hover:brightness-125 shadow-xl shadow-[#0D1B3E]/30 active:scale-95 transition-all uppercase tracking-widest"
                                      >Download</button>
                                    </div>
                                   )}
                                   {run.bankingReportKey && (
                                     <div className="group flex items-center justify-between rounded-[2rem] border border-[#0ABFBC]/10 bg-[#0ABFBC]/5 p-5 transition-all hover:shadow-2xl hover:shadow-[#0ABFBC]/10 hover:-translate-y-1">
                                      <div className="flex items-center gap-5">
                                        <div className="w-12 h-12 rounded-2xl bg-white shadow-xl shadow-slate-200/50 flex items-center justify-center text-2xl group-hover:scale-110 transition-transform">📋</div>
                                        <div>
                                            <div className="text-sm font-black text-[#0ABFBC] italic uppercase tracking-tighter">Management Banking Report</div>
                                            <div className="text-[10px] text-[#0ABFBC] font-bold tracking-widest">Decision Ready Assets</div>
                                        </div>
                                      </div>
                                      <button 
                                        onClick={() => handleDownload(run.bankingReportKey!)}
                                        className="rounded-2xl bg-[#0ABFBC] px-6 py-3 text-[10px] font-black text-white hover:brightness-125 shadow-xl shadow-[#0ABFBC]/30 active:scale-95 transition-all uppercase tracking-widest"
                                      >Download</button>
                                    </div>
                                   )}
                                </>
                              ) : (
                                <div className="flex flex-col items-center justify-center p-16 rounded-[2.5rem] bg-slate-50 border border-slate-100">
                                   <div className="relative">
                                       <motion.div 
                                         animate={{ rotate: 360 }}
                                         transition={{ repeat: Infinity, duration: 4, ease: "linear" }}
                                         className="w-12 h-12 border-4 border-[#0ABFBC]/10 border-t-[#0ABFBC] rounded-full"
                                       />
                                       <div className="absolute inset-0 flex items-center justify-center text-xs opacity-50">🤖</div>
                                   </div>
                                   <span className="text-[10px] font-black text-slate-400 italic uppercase tracking-[0.2em] mt-6">AI Asset Computation In Progress...</span>
                                </div>
                              )}
                           </div>
                        </div>

                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>

      </div>
    </div>
  );
}

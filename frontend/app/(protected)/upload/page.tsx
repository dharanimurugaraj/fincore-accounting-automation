"use client"

import { useState, useEffect, useRef } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { api, API_BASE } from "@/lib/api"
import { useAuth } from "@/components/auth/AuthContext"

interface ProgressState {
  step: string
  status: "idle" | "running" | "done" | "error" | "complete"
  detail: string
  percent: number
  sub_steps: string[]
  downloads?: {
    working_sheet: string
    banking_report: string
  }
  validation?: any
}

interface ORKeyInfo {
  data?: {
    usage: number
    limit: number | null
    is_free_tier: boolean
  }
  error?: string
}

const PIPELINE_STEPS = [
  {
    id: "upload",
    label: "Uploading Files",
    icon: "📤",
    description: "Receiving and saving PDF files"
  },
  {
    id: "validation",
    label: "Validating Bank Statements",
    icon: "🔍",
    description: "Confirming PDFs are valid bank statements"
  },
  {
    id: "extraction",
    label: "Extracting Transactions",
    icon: "🤖",
    description: "AI reading all transaction data"
  },
  {
    id: "computation",
    label: "Running Financial Formulas",
    icon: "🧮",
    description: "Computing CC interest, WCDL, Finance Cost"
  },
  {
    id: "working_sheet",
    label: "Generating Working Sheet",
    icon: "📊",
    description: "Building Excel with all calculations"
  },
  {
    id: "banking_report",
    label: "Generating Banking Report",
    icon: "📋",
    description: "Building management report Excel"
  },
  {
    id: "complete",
    label: "Complete",
    icon: "🎉",
    description: "Files ready for download"
  }
]

export default function UploadPage() {
  const { profile } = useAuth()
  const [files, setFiles] = useState<File[]>([])
  const [jobId, setJobId] = useState<string | null>(null)
  const [progress, setProgress] = useState<ProgressState | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [creditInfo, setCreditInfo] = useState<ORKeyInfo | null>(null)
  const [loadingCredits, setLoadingCredits] = useState(false)
  const eventSourceRef = useRef<EventSource | null>(null)
  
  // 1. Phase 3: Keep-Warm Strategy
  useEffect(() => {
    // Ping the backend on mount to ensure serverless functions are warm
    api.get("health").catch(() => {});
    if (profile?.role === "SUPER_ADMIN") {
      fetchCredits();
    }
  }, [profile?.role]);

  const fetchCredits = async () => {
    setLoadingCredits(true);
    try {
      const data = await api.get<any>("settings/credits");
      // settings/credits returns { data: { total_credits, total_usage, ... } } or { error }
      if (data.data) {
        setCreditInfo({
          data: {
            usage: data.data.total_usage,
            limit: data.data.total_credits,
            is_free_tier: data.data.is_free_tier || false
          }
        });
      }
    } catch (err) {
      console.error("Failed to fetch credits:", err);
    } finally {
      setLoadingCredits(false);
    }
  };

  // Recover job dynamically from Backend (Layer 2 - No Hardcoding)
  useEffect(() => {
    const checkActiveJob = async () => {
      try {
        const data = await api.get<{ job_id: string | null }>("process/active");
        if (data.job_id) {
          console.log("Dynamically recovered active job:", data.job_id);
          setJobId(data.job_id);
        }
      } catch (err) {
        console.error("Failed to recover active job:", err);
      }
    };
    checkActiveJob();
  }, []);

  const handleUpload = async () => {
    if (!files.length) return

    // Credit Guard
    if (creditInfo?.data) {
        const remaining = (creditInfo.data.limit || 0) - creditInfo.data.usage;
        const totalEstimatedCost = files.length * 0.05; // $0.05 per PDF estimate
        
        if (remaining <= 0) {
            alert("NO OPENROUTER_API_KEY low balance please do check. Your balance is exhausted.");
            return;
        }

        if (remaining < totalEstimatedCost) {
            const supportedCount = Math.floor(remaining / 0.05);
            alert(`Insufficient balance: credits support ~${supportedCount} more PDFs, but ${files.length} were uploaded. Please check your OpenRouter account.`);
            return;
        }
    }

    const formData = new FormData()
    files.forEach(f => formData.append("files", f))

    try {
        const data = await api.postForm<any>("process", formData)
        
        if (data.error) {
            alert(data.error)
            return
        }
        
        const job_id = data.job_id
        if (!job_id) {
            console.error("No Job ID returned from server")
            return
        }
        console.log("Job started:", job_id)
        setJobId(job_id)
    } catch (err) {
        console.error("Upload error:", err)
        alert("Failed to start processing")
    }
  }

  // 3. Phase 4: SSE Migration (Server-Sent Events)
  useEffect(() => {
    if (!jobId || progress?.status === "complete" || progress?.status === "error") return;

    // We MUST pass the token as a query param because EventSource doesn't support custom headers
    const token = localStorage.getItem("fincore_token");
    const sseUrl = `${API_BASE}/process/progress/${jobId}?token=${token}`;
    
    console.log("[SSE] Connecting to:", sseUrl);
    const eventSource = new EventSource(sseUrl);
    eventSourceRef.current = eventSource;

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log("[SSE] Update received:", data);

        if (data.status === "idle" && !progress) return;

        const isApproved = data.status === "APPROVED" || data.status === "complete";
        const isFailed = data.status === "FAILED" || data.status === "VALIDATION_FAILED" || data.status === "ERROR";

        // Map backend response to ProgressState
        const mappedProgress: ProgressState = {
          step: isApproved ? "complete" : (data.step || progress?.step || "upload"),
          status: isApproved ? "complete" : isFailed ? "error" : "running",
          detail: data.message || "Processing...",
          percent: data.percent || 0,
          sub_steps: data.sub_steps || [],
          downloads: data.downloads
        };

        // If backend didn't send step, try to extract from message prefix [STEP]
        if (!data.step && data.message) {
            const stepMatch = data.message.match(/^\[(\w+)\]/);
            if (stepMatch) mappedProgress.step = stepMatch[1].toLowerCase();
        }

        setProgress(mappedProgress);

        if (isApproved || isFailed) {
          console.log("[SSE] Closing connection (Job Terminal State)");
          eventSource.close();
        }
      } catch (err) {
        console.error("[SSE] Parse error:", err);
      }
    };

    eventSource.onerror = (err) => {
      console.error("[SSE] Connection error:", err);
      // EventSource automatically retries, but we might want to fall back to polling if it fails repeatedly
      // For now, let's just log it.
    };

    return () => {
      console.log("[SSE] Cleaning up connection");
      eventSource.close();
    };
  }, [jobId]);

  // Initial Sync Fallback (If SSE hasn't pushed yet)
  useEffect(() => {
    if (jobId && !progress) {
        const sync = async () => {
            try {
                const data = await api.get<any>(`process/status/${jobId}`);
                if (data.status) {
                    // Pre-map the initial status so UI doesn't look empty while SSE connects
                    const rawMessage = data.progress?.message || "";
                    const stepMatch = rawMessage.match(/^\[(\w+)\]/);
                    const detail = rawMessage.replace(/^\[\w+\]\s*/i, "") || "Connected to processing stream...";
                    
                    const isComplete = data.status === "APPROVED" || data.status === "complete";
                    setProgress({
                        step: isComplete ? "complete" : (stepMatch ? stepMatch[1].toLowerCase() : "upload"),
                        status: isComplete ? "complete" : "running",
                        detail,
                        percent: data.progress?.percent || 5,
                        sub_steps: data.progress?.sub_steps || [],
                        downloads: data.working_sheet && data.banking_report ? {
                            working_sheet: data.working_sheet,
                            banking_report: data.banking_report
                        } : undefined
                    });
                }
            } catch(e) {}
        };
        sync();
    }
  }, [jobId]);

  const getStepStatus = (stepId: string) => {
    if (!progress) return "idle"
    const currentIdx = PIPELINE_STEPS.findIndex(s => s.id === progress.step)
    const thisIdx = PIPELINE_STEPS.findIndex(s => s.id === stepId)
    
    if (thisIdx < currentIdx) return "done"
    if (thisIdx === currentIdx) return progress.status
    if (progress.status === "complete") return "done"
    return "idle"
  }

  return (
    <div className="min-h-screen bg-neutral-app text-t-body p-4 md:p-8 rounded-3xl">
      <div className="max-w-3xl mx-auto">
        
        {/* Header */}
        <div className="mb-10 text-center">
          <h1 className="text-4xl font-black mb-3 bg-gradient-to-r from-ai-teal to-ai-violet bg-clip-text text-transparent italic tracking-tight">
            FINCORE INTELLIGENCE
          </h1>
          <p className="text-t-muted text-sm font-medium">
            Enterprise-grade banking extraction. Process up to 10 PDFs (100 pages each) simultaneously.
          </p>
        </div>

        {/* Upload zone */}
        {!jobId && (
          <div
            className={`border-2 border-dashed rounded-[2.5rem] p-16 text-center mb-8 transition-all duration-500 shadow-xl shadow-neutral-border/50 ${
              isDragging
                ? "border-ai-violet bg-ai-violet/5 scale-[1.01]"
                : "border-neutral-border bg-white hover:border-ai-violet/50"
            }`}
            onDragOver={(e) => {
              e.preventDefault()
              setIsDragging(true)
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={(e) => {
              e.preventDefault()
              setIsDragging(false)
              const dropped = Array.from(e.dataTransfer.files)
                .filter(f => f.type === "application/pdf")
              setFiles(prev => [...prev, ...dropped])
            }}
          >
            <div className="w-16 h-16 bg-neutral-app rounded-2xl flex items-center justify-center text-3xl mx-auto mb-6 shadow-inner">📄</div>
            <p className="text-t-heading mb-2 font-bold text-lg">
              Drop bank statements here
            </p>
            <p className="text-t-muted text-xs mb-10 font-medium italic">
              All major Indian banks supported (HDFC, SBI, ICICI, etc.)
            </p>
            <label className="cursor-pointer inline-flex items-center gap-2 px-10 py-4 bg-ai-violet text-white rounded-2xl font-black text-sm uppercase tracking-widest hover:brightness-110 transition-all active:scale-95 shadow-xl shadow-ai-violet/30">
              Select Files
              <input
                type="file"
                multiple
                accept=".pdf"
                className="hidden"
                onChange={(e) => {
                  const selected = Array.from(e.target.files || [])
                  setFiles(prev => [...prev, ...selected])
                }}
              />
            </label>
          </div>
        )}

        {/* File list */}
        {files.length > 0 && !jobId && (
          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-8 space-y-3"
          >
            {files.map((file, i) => (
              <div
                key={i}
                className="flex items-center justify-between bg-white border border-neutral-border rounded-[1.5rem] px-6 py-5 shadow-sm"
              >
                <div className="flex items-center gap-5">
                  <div className="w-12 h-12 bg-ai-violet/5 rounded-2xl flex items-center justify-center text-2xl">📄</div>
                  <div>
                    <div className="text-sm font-bold text-t-heading">{file.name}</div>
                    <div className="text-[10px] text-t-muted font-black uppercase tracking-[0.15em] mt-0.5">{(file.size / 1024 / 1024).toFixed(2)} MB</div>
                  </div>
                </div>
                <button
                  onClick={() => setFiles(f => f.filter((_, idx) => idx !== i))}
                  className="w-10 h-10 flex items-center justify-center rounded-xl text-t-muted hover:text-status-critical hover:bg-status-critical/10 transition-all"
                >
                  ✕
                </button>
              </div>
            ))}
            
            <button
              onClick={handleUpload}
              className="w-full mt-10 py-5 bg-t-heading text-white rounded-[2rem] font-black text-xs uppercase tracking-[0.3em] hover:bg-ai-violet transition-all active:scale-[0.98] shadow-2xl shadow-t-heading/20"
            >
              Analyze Statements →
            </button>
          </motion.div>
        )}

        {/* Live Progress */}
        <AnimatePresence>
          {jobId && (
            <motion.div
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              className="space-y-6"
            >
              <div className="mb-10 bg-white p-8 rounded-[2.5rem] border border-neutral-border shadow-xl shadow-neutral-border/50">
                <div className="flex justify-between items-center text-[10px] font-black uppercase tracking-[0.2em] text-t-muted mb-4">
                  <div className="flex items-center gap-4">
                    <span>Overall Pipeline Progress</span>
                    <button 
                        onClick={() => {
                            setJobId(null);
                            setProgress(null);
                            setFiles([]);
                        }}
                        className="text-status-critical hover:underline transition-all lowercase italic font-medium"
                    >(Reset / Stop)</button>
                  </div>
                  <span className="text-ai-violet bg-ai-violet/10 px-2 py-0.5 rounded-md font-black italic">{progress?.percent ?? 0}%</span>
                </div>
                <div className="h-3 bg-neutral-app rounded-full overflow-hidden relative">
                  <motion.div
                    className="h-full bg-gradient-to-r from-ai-teal to-ai-violet rounded-full relative z-10"
                    animate={{ width: `${progress?.percent ?? 0}%` }}
                    transition={{ duration: 0.8, ease: "circOut" }}
                  />
                  {/* Subtle Background Glow for active progress */}
                  <motion.div 
                    className="absolute top-0 left-0 h-full bg-ai-violet/20 blur-sm"
                    animate={{ width: `${progress?.percent ?? 0}%` }}
                  />
                </div>
              </div>

              <div className="relative space-y-4">
                {/* Vertical Timeline Line */}
                <div className="absolute left-[30px] top-6 bottom-6 w-[2px] bg-neutral-border z-0"></div>

                {PIPELINE_STEPS.map((step, idx) => {
                  const status = getStepStatus(step.id)
                  const isActive = status === "running"
                  const isDone = status === "done" || (step.id === "complete" && progress?.status === "complete")
                  const isError = status === "error"

                  return (
                    <motion.div
                      key={step.id}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: idx * 0.05 }}
                      className={`relative z-10 rounded-[2rem] border p-6 transition-all duration-500 shadow-sm ${
                        isActive
                          ? "border-ai-violet/30 bg-ai-violet/5 shadow-xl shadow-ai-violet/5 scale-[1.02]"
                          : isDone
                          ? "border-status-success/20 bg-white"
                          : isError
                          ? "border-status-critical/20 bg-status-critical/5"
                          : "border-neutral-border bg-white"
                      }`}
                    >
                      <div className="flex items-center gap-5">
                        <div className={`w-12 h-12 rounded-2xl flex items-center justify-center text-sm flex-shrink-0 transition-all duration-700 z-10 ${
                          isActive ? "bg-ai-violet text-white shadow-lg shadow-ai-violet/40" :
                          isDone ? "bg-status-success text-white shadow-lg shadow-status-success/40" :
                          isError ? "bg-status-critical text-white shadow-lg shadow-status-critical/40" :
                          "bg-white border-2 border-neutral-border text-t-heading"
                        }`}>
                          {isActive ? (
                            <motion.div
                              animate={{ rotate: 360 }}
                              transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
                              className="w-5 h-5 border-2 border-white border-t-transparent rounded-full"
                            />
                          ) : isDone ? (
                            <motion.span 
                                initial={{ scale: 0 }}
                                animate={{ scale: 1 }}
                                className="text-xl font-black"
                            >✓</motion.span>
                          ) : isError ? (
                            <span className="text-xl">✕</span>
                          ) : (
                            <span className="font-bold text-t-heading/40 italic select-none">{idx + 1}</span>
                          )}
                        </div>

                        <div className="flex-1 min-w-0">
                          <div className={`text-xs font-black tracking-[0.15em] uppercase ${
                            isActive ? "text-ai-violet" :
                            isDone ? "text-t-muted" :
                            isError ? "text-status-critical" :
                            "text-t-muted/40"
                          }`}>
                            {step.label}
                          </div>
                          {isActive && progress?.detail && (
                            <motion.p
                              initial={{ opacity: 0 }}
                              animate={{ opacity: 1 }}
                              className="text-[11px] text-t-body mt-1 font-bold italic"
                            >
                              {progress.detail}
                            </motion.p>
                          )}
                        </div>
                        
                        {isActive && (
                            <motion.div 
                                animate={{ opacity: [0.3, 1, 0.3] }}
                                transition={{ repeat: Infinity, duration: 1.5 }}
                                className="px-2 py-1 bg-ai-violet text-[8px] text-white rounded-md font-black uppercase"
                            >Live</motion.div>
                        )}
                      </div>

                      {isActive && progress?.sub_steps && progress.sub_steps.length > 0 && (
                        <motion.div
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: "auto" }}
                          className="mt-6 ml-16 space-y-3"
                        >
                          {progress?.sub_steps?.map((sub, i) => {
                            const isLive = sub.includes("⚡") || sub.includes("...") || sub.includes("Analyzing") || sub.includes("Validating");
                            const isDone = sub.includes("✓");
                            
                            return (
                              <motion.div
                                key={sub}
                                initial={{ opacity: 0, x: -5 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: i * 0.05 }}
                                className="text-[11px] font-bold text-t-body flex items-center justify-between group"
                              >
                                <div className="flex items-center gap-3">
                                  <span className={`w-1 h-1 rounded-full transition-all duration-500 ${isLive ? "bg-ai-violet animate-pulse scale-125 shadow-md shadow-ai-violet/50" : isDone ? "bg-status-success" : "bg-neutral-border"}`}></span>
                                  <span className={`tracking-tight ${isLive ? "text-t-heading" : "text-t-muted/80"}`}>{sub.replace(/[⚡✓]/g, "").trim()}</span>
                                </div>
                                {isLive && (
                                  <span className="px-1.5 py-0.5 bg-ai-violet/10 rounded text-[9px] text-ai-violet font-black uppercase italic tracking-wider">Processing</span>
                                )}
                              </motion.div>
                            );
                          })}
                        </motion.div>
                      )}
                    </motion.div>
                  )
                })}
              </div>

              {progress?.status === "complete" && progress?.downloads && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mt-12 p-10 bg-white border border-neutral-border rounded-[3rem] shadow-2xl shadow-neutral-border/20 text-center"
                >
                  <div className="w-16 h-16 bg-status-success/10 rounded-2xl flex items-center justify-center text-3xl mx-auto mb-6 shadow-xl shadow-status-success/10">✨</div>
                  <h3 className="text-t-heading text-2xl font-black mb-2 italic">Analysis Succeeded</h3>
                  <p className="text-t-muted text-xs font-medium mb-10">Reports are ready. AI verified all transactions and formulas.</p>
                  <div className="flex flex-col sm:flex-row gap-5">
                    <button
                      onClick={() => {
                        const token = localStorage.getItem("fincore_token");
                        const url = `/api/process/download?path=${encodeURIComponent(progress.downloads!.working_sheet)}&token=${token}`;
                        window.open(url, "_blank");
                      }}
                      className="flex-1 py-5 bg-t-heading text-white rounded-[2rem] text-[10px] font-black uppercase tracking-[0.25em] text-center hover:brightness-110 transition-all shadow-xl shadow-t-heading/30 active:scale-95"
                    >📊 Working Sheet</button>
                    <button
                      onClick={() => {
                        const token = localStorage.getItem("fincore_token");
                        const url = `/api/process/download?path=${encodeURIComponent(progress.downloads!.banking_report)}&token=${token}`;
                        window.open(url, "_blank");
                      }}
                      className="flex-1 py-5 bg-ai-violet text-white rounded-[2rem] text-[10px] font-black uppercase tracking-[0.25em] text-center hover:brightness-110 transition-all shadow-xl shadow-ai-violet/30 active:scale-95"
                    >📋 Banking Report</button>
                  </div>
                </motion.div>
              )}

              {progress?.status === "error" && (
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mt-10 p-10 bg-status-critical/5 border border-status-critical/10 rounded-[3rem] text-center"
                >
                    <div className="text-4xl mb-6">🚨</div>
                    <h3 className="text-status-critical font-black mb-3 text-xl italic uppercase tracking-tight">Processing Aborted</h3>
                    <div className="bg-white/50 p-4 rounded-2xl border border-status-critical/20 mb-8 mt-4">
                        <p className="text-status-critical text-xs font-black tracking-tight">{progress.detail}</p>
                    </div>
                    <button 
                        onClick={() => {setJobId(null); setProgress(null); setFiles([]);}}
                        className="px-10 py-4 bg-status-critical text-white rounded-2xl font-black text-xs uppercase tracking-[0.2em] transition-all hover:bg-status-critical/80 shadow-xl shadow-status-critical/20"
                    >Restart Pipeline</button>
                </motion.div>
              )}

              {progress?.status === "complete" && (
                <div className="mt-8 text-center pb-20">
                    <button 
                        onClick={() => {setJobId(null); setProgress(null); setFiles([]);}}
                        className="px-10 py-4 bg-neutral-app text-t-muted rounded-2xl font-black text-[10px] uppercase tracking-[0.2em] transition-all hover:bg-neutral-border"
                    >Analyze Another Statement</button>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

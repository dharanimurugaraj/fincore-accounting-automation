"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { 
  Cpu, 
  Search, 
  Save, 
  RefreshCw, 
  ShieldCheck, 
  Zap, 
  Layers, 
  Database,
  ArrowRight
} from "lucide-react";

const AGENTS = [
  { id: "hdfc_cc_agent", label: "HDFC CC Agent", desc: "Specialized in HDFC Credit Card PDF and for precise table extraction." },
  { id: "ubi_ca_agent", label: "UBI CA Agent", desc: "High-performance extractor for Union Bank Current Accounts." },
  { id: "sbi_sb_agent", label: "SBI SB Agent", desc: "Stable SBI Savings Bank and for standard bank statement mapping." },
  { id: "forex_agent", label: "Forex Specialist", desc: "Captures currency exchange and for cross-border remittance tables." },
  { id: "wcdl_agent", label: "WCDL Logic Agent", desc: "Financial parser for Working Capital Demand Loan schedules." },
  { id: "generic_bank_agent", label: "Generic Bank Core", desc: "Universal fallback and for uncommon banking formats." }
];

const PROVIDERS = ["OpenAI", "Anthropic", "Google", "DeepSeek", "Meta", "NVIDIA", "Qwen"];

export default function AdminModelsPage() {
  const [configs, setConfigs] = useState<Record<string, any>>({});
  const [allModels, setAllModels] = useState<any[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [saving, setSaving] = useState<string | null>(null);
  const [globalLoading, setGlobalLoading] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setGlobalLoading(true);
    try {
      const [modelsRes, configRes] = await Promise.all([
        api.get<any>("admin/models/external"),
        api.get<any>("admin/models/config")
      ]);
      
      const models = modelsRes?.data || [];
      const configs_list = configRes?.configs || [];
      
      setAllModels(models);
      
      const configMap: Record<string, any> = {};
      (configs_list || []).forEach((c: any) => {
        configMap[c.agentId] = c;
      });
      setConfigs(configMap);
    } catch (e) {
      console.error("Failed to fetch model configs:", e);
    } finally {
      setGlobalLoading(false);
    }
  };

  const handleUpdate = (agentId: string, field: string, value: any) => {
    setConfigs(prev => ({
      ...prev,
      [agentId]: { ...prev[agentId], [field]: value }
    }));
  };

  const saveConfig = async (agentId: string) => {
    setSaving(agentId);
    try {
      const config = configs[agentId];
      if (!config) return;
      
      await api.post("admin/models/config", {
         agent_id: agentId,
         primary_model: config.primaryModel,
         fallback_models: config.fallbackModels,
         max_retries: config.maxRetries || 3,
         temperature: config.temperature || 0.0
      });
      fetchData();
    } catch (e) {
      console.error("Save failed:", e);
    } finally {
      setSaving(null);
    }
  };

  const handleGlobalSync = async (modelId: string) => {
    if(!modelId) return;
    setGlobalLoading(true);
    try {
      for (const agent of AGENTS) {
        await api.post("admin/models/config", { 
            agent_id: agent.id, 
            primary_model: modelId,
            fallback_models: ["openai/gpt-4o-mini"],
            max_retries: 3 
        });
      }
      await fetchData();
    } catch (e) {
      console.error("Global sync failed:", e);
    } finally {
      setGlobalLoading(false);
    }
  };

  const groupModelsByProvider = (models: any[]) => {
    const groups: Record<string, any[]> = {};
    models.forEach(m => {
      let provider = "Others";
      const mid = m.id.toLowerCase();
      if (mid.includes("openai") || mid.startsWith("gpt-")) provider = "OpenAI";
      else if (mid.includes("anthropic") || mid.startsWith("claude-")) provider = "Anthropic";
      else if (mid.includes("google") || mid.startsWith("gemini-")) provider = "Google";
      else if (mid.includes("deepseek")) provider = "DeepSeek";
      else if (mid.includes("meta") || mid.startsWith("llama-")) provider = "Meta";
      else if (mid.includes("nvidia")) provider = "NVIDIA";
      else if (mid.includes("qwen")) provider = "Qwen";
      
      if (!groups[provider]) groups[provider] = [];
      groups[provider].push(m);
    });
    return groups;
  };

  const groupedModels = groupModelsByProvider(allModels);

  const ModelSelector = ({ label, value, onChange, borderClass }: any) => {
    const filtered = allModels.filter(m => 
      m.id.toLowerCase().includes(searchQuery.toLowerCase()) || 
      (m.name || "").toLowerCase().includes(searchQuery.toLowerCase())
    );

    return (
      <div className="space-y-2">
        <label className="text-[10px] font-bold uppercase tracking-widest text-t-muted flex items-center gap-2">
          <Zap className="h-3 w-3 text-primary" />
          {label}
        </label>
        <select 
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className={`w-full bg-neutral-app/50 border border-neutral-border rounded-xl py-2.5 px-4 text-xs text-t-heading outline-none appearance-none focus:ring-1 focus:ring-primary/20 transition-all font-medium ${borderClass}`}
        >
          <option value="">Default (Provider Handover)</option>
          {filtered.slice(0, 100).map((m, idx) => (
            <option key={`${m.id}-${idx}`} value={m.id}>{m.name || m.id}</option>
          ))}
        </select>
      </div>
    );
  };

  return (
    <div className="max-w-7xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700 pb-24">
      {/* Header Pulse */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 border-b border-neutral-border pb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-t-heading flex items-center gap-3">
            <Cpu className="h-8 w-8 text-primary" />
            AI Governance Fleet
          </h1>
          <p className="text-t-muted mt-1">High-performance AI model routing and for cross-bank extraction nodes.</p>
        </div>

        <div className="flex items-center gap-3">
          <button 
            onClick={fetchData}
            className="p-2.5 rounded-xl border border-neutral-border bg-neutral-card hover:bg-neutral-border transition-all group"
          >
            <RefreshCw className={`h-4 w-4 text-t-body group-hover:text-primary transition-colors ${globalLoading ? "animate-spin" : ""}`} />
          </button>
          <div className="px-4 py-2 rounded-xl bg-status-success/10 text-status-success text-[10px] font-bold uppercase tracking-widest border border-status-success/20">
            {allModels.length} Engines Live
          </div>
        </div>
      </div>

      {/* Global Master Pulse Command Card */}
      <div className="relative overflow-hidden rounded-3xl border border-ai-violet/30 bg-ai-violet/5 p-8 backdrop-blur-xl">
          <div className="relative z-10 flex flex-col md:flex-row items-center justify-between gap-8">
              <div className="flex items-center gap-6">
                <div className="p-4 rounded-2xl bg-ai-violet text-neutral-app shadow-lg">
                    <RefreshCw className={`h-8 w-8 ${globalLoading ? "animate-spin" : ""}`} />
                </div>
                <div>
                    <h2 className="text-2xl font-bold text-t-heading uppercase tracking-tighter">Master Synchronizer</h2>
                    <p className="text-t-muted text-sm mt-1">Simultaneously update all 6 banking extraction nodes to a specific AI core.</p>
                </div>
              </div>
              
              <div className="flex items-center gap-4 w-full md:w-auto">
                <div className="flex-1 md:w-64 relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-t-muted" />
                  <input 
                    type="text"
                    placeholder="Search master engine..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full bg-neutral-app/80 border border-neutral-border rounded-xl py-2.5 pl-10 pr-4 text-xs outline-none focus:border-ai-violet/50 transition-all font-medium"
                  />
                </div>
                <button 
                  disabled={globalLoading}
                  onClick={() => {
                    const firstAgent = AGENTS[0].id;
                    const model = configs[firstAgent]?.primaryModel;
                    if(model) handleGlobalSync(model);
                  }}
                  className="bg-ai-violet text-neutral-app px-8 py-3 rounded-xl font-bold text-[10px] uppercase tracking-widest hover:bg-ai-violet-hover transition-all active:scale-95 shadow-xl disabled:opacity-50"
                >
                  Sync Global Fleet
                </button>
              </div>
          </div>
          <div className="absolute right-0 top-0 h-full w-32 bg-gradient-to-l from-ai-violet/10 to-transparent" />
      </div>

      {/* AI Provider Searchable Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {PROVIDERS.map(provider => {
          const models = groupedModels[provider] || [];
          return (
            <div key={provider} className="rounded-3xl border border-neutral-border bg-neutral-card/10 p-6 hover:shadow-xl transition-all border-dashed group">
               <div className="flex items-center justify-between mb-4 border-b border-neutral-border/30 pb-4">
                  <h4 className="font-bold text-t-heading uppercase tracking-widest text-[11px]">{provider}</h4>
                  <span className="text-[10px] font-bold text-primary">{models.length} Nodes</span>
               </div>
               <select 
                  onChange={(e) => handleGlobalSync(e.target.value)}
                  className="w-full bg-neutral-app/40 border border-neutral-border rounded-xl px-3 py-2 text-xs text-t-body outline-none focus:border-primary/50 transition-all cursor-pointer"
               >
                  <option value="">Choose Registry Core...</option>
                  {models.slice(0, 30).map((m: any, idx: number) => (
                    <option key={`${m.id}-${idx}`} value={m.id}>{m.name || m.id}</option>
                  ))}
               </select>
            </div>
          );
        })}
      </div>

      <div className="flex items-center gap-3 pt-6 border-t border-neutral-border/50">
        <h2 className="text-xl font-bold text-t-heading uppercase tracking-tighter">Node Detail Mapping</h2>
        <div className="h-px flex-1 bg-neutral-border/50" />
      </div>

      {/* Detail Node Cards */}
      <div className="grid grid-cols-1 gap-6">
        {AGENTS.map((agent) => {
          const config = configs[agent.id] || { 
            agentId: agent.id, 
            primaryModel: "openai/gpt-4o", 
            fallbackModels: ["openai/gpt-4o-mini"], 
            maxRetries: 3 
          };
          
          return (
            <div 
              key={agent.id} 
              className="rounded-3xl border border-neutral-border bg-neutral-card/30 p-8 backdrop-blur-xl hover:border-ai-violet/30 transition-all group"
            >
              <div className="flex flex-col lg:flex-row gap-8">
                <div className="lg:w-1/3">
                  <div className="flex items-center gap-3 mb-2">
                    <div className="p-2 rounded-xl bg-ai-violet/10 text-ai-violet group-hover:scale-110 transition-transform">
                      <Layers className="h-4 w-4" />
                    </div>
                    <h3 className="font-bold text-t-heading uppercase tracking-widest text-xs">{agent.label}</h3>
                  </div>
                  <p className="text-[11px] text-t-muted leading-relaxed font-medium uppercase tracking-tight">{agent.desc}</p>
                </div>

                <div className="flex-1 space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <ModelSelector 
                      label="Primary Extraction Core"
                      value={config.primaryModel}
                      onChange={(val: string) => handleUpdate(agent.id, "primaryModel", val)}
                      borderClass="focus:border-primary/50"
                    />

                    <ModelSelector 
                      label="Secondary Fallback Pulse"
                      value={config.fallbackModels[0] || ""}
                      onChange={(val: string) => {
                        const newFallbacks = [...(config.fallbackModels || [])];
                        newFallbacks[0] = val;
                        handleUpdate(agent.id, "fallbackModels", newFallbacks);
                      }}
                      borderClass="focus:border-status-medium/50"
                    />

                    <ModelSelector 
                      label="Tertiary Resilience Node"
                      value={config.fallbackModels[1] || ""}
                      onChange={(val: string) => {
                        const newFallbacks = [...(config.fallbackModels || [])];
                        newFallbacks[1] = val;
                        handleUpdate(agent.id, "fallbackModels", newFallbacks);
                      }}
                      borderClass="focus:border-status-critical/50"
                    />
                  </div>

                  <div className="flex items-center justify-end pt-4 gap-4 border-t border-neutral-border/50">
                    <button
                      onClick={() => saveConfig(agent.id)}
                      disabled={saving === agent.id}
                      className="flex items-center gap-2 rounded-xl bg-neutral-border px-5 py-2.5 text-[10px] font-bold text-t-heading uppercase tracking-widest transition-all hover:bg-primary hover:text-neutral-app active:scale-95 disabled:opacity-50"
                    >
                      {saving === agent.id ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                      {saving === agent.id ? "Syncing..." : "Update Node"}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

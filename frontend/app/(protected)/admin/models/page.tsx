"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/components/auth/AuthContext";
import { 
  Cpu, 
  Layers, 
  DollarSign, 
  Search, 
  Filter, 
  RefreshCw, 
  ShieldCheck, 
  Zap,
  Globe,
  Settings2,
  ChevronRight
} from "lucide-react";
import { api } from "@/lib/api";

interface ORModel {
  id: string;
  name: string;
  pricing: {
    prompt: string;
    completion: string;
  };
  context_length: number;
  description: string;
}

interface AgentConfig {
  agentId: string;
  primaryModel: string;
  fallbackModels: string[];
  maxRetries: number;
  temperature: number;
}

const AGENTS = [
  { id: "hdfc_cc", name: "HDFC CC Agent", type: "Bank Statement" },
  { id: "hdfc_ca", name: "HDFC Current Agent", type: "Bank Statement" },
  { id: "ubi_ca", name: "UBI Current Agent", type: "Bank Statement" },
  { id: "wcdl_parser", name: "WCDL Advice Parser", type: "Advice Letter" },
  { id: "forex_parser", name: "Forex Advice Parser", type: "Advice Letter" },
  { id: "general_ocr", name: "General OCR Dispatch", type: "System" },
];

export default function AdminModelsPage() {
  const [extModels, setExtModels] = useState<ORModel[]>([]);
  const [configs, setConfigs] = useState<AgentConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);

  const { profile } = useAuth(); // Import useAuth at top!

  const fetchData = async () => {
    setLoading(true);
    try {
      const [extRes, cfgRes] = await Promise.all([
        api.get<{ data: ORModel[] }>("admin/models/external"),
        api.get<{ configs: AgentConfig[] }>("admin/models/config")
      ]);
      if (extRes?.data) setExtModels(extRes.data);
      if (cfgRes?.configs) setConfigs(cfgRes.configs);
    } catch (err) {
      console.error("Failed to fetch models:", err);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchData();
  }, []);

  const assignPrimary = async (agentId: string, modelId: string) => {
    const existing = configs.find(c => c.agentId === agentId);
    try {
      await api.post("admin/models/config", {
        agent_id: agentId,
        primary_model: modelId,
        fallback_models: existing?.fallbackModels || [],
        max_retries: existing?.maxRetries || 3,
        temperature: existing?.temperature || 0.0
      });
      fetchData();
    } catch (err) {
      console.error("Model update failed:", err);
    }
  };

  const assignFallback = async (agentId: string, modelId: string) => {
    const existing = configs.find(c => c.agentId === agentId);
    let fallbacks = [...(existing?.fallbackModels || [])];
    if (!fallbacks.includes(modelId)) fallbacks.push(modelId);
    
    try {
      await api.post("admin/models/config", {
        agent_id: agentId,
        primary_model: existing?.primaryModel || "gemini-2.5-flash-lite",
        fallback_models: fallbacks,
        max_retries: existing?.maxRetries || 3,
        temperature: existing?.temperature || 0.0
      });
      fetchData();
    } catch (err) {
      console.error("Fallback update failed:", err);
    }
  };

  const removeFallback = async (agentId: string, modelIdToRemove: string) => {
    const existing = configs.find(c => c.agentId === agentId);
    if (!existing) return;
    
    const fallbacks = existing.fallbackModels.filter(m => m !== modelIdToRemove);
    try {
      await api.post("admin/models/config", {
        agent_id: agentId,
        primary_model: existing.primaryModel,
        fallback_models: fallbacks,
        max_retries: existing.maxRetries,
        temperature: existing.temperature
      });
      fetchData();
    } catch (err) {
      console.error("Fallback removal failed:", err);
    }
  };

  const filteredModels = extModels.filter(m => 
    m.id.toLowerCase().includes(search.toLowerCase()) || 
    m.name.toLowerCase().includes(search.toLowerCase())
  );

  if (profile?.role_id !== 0) {
      return (
          <div className="flex items-center justify-center h-[calc(100vh-10rem)] w-full">
              <div className="text-center space-y-4">
                  <ShieldCheck className="h-16 w-16 text-rose-500/50 mx-auto" />
                  <h2 className="text-2xl font-bold text-slate-200 tracking-wider uppercase">Restricted Core Domain</h2>
                  <p className="text-sm text-slate-500 max-w-md mx-auto">AI Model mapping configurations are restricted strictly to Super Administrators (Role 0) to prevent unauthorized cost escalation.</p>
              </div>
          </div>
      )
  }

  return (
    <div className="flex flex-col h-[calc(100vh-12rem)] space-y-6">
      {/* Header Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
         {/* ...stats remain identical */}
         <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
            <div className="flex items-center gap-2 text-slate-500 mb-1">
               <Cpu className="h-4 w-4" />
               <span className="text-[10px] font-semibold uppercase tracking-wider">Models Catalog</span>
            </div>
            <p className="text-2xl font-bold text-slate-100">{extModels.length}</p>
            <p className="text-[10px] text-slate-500">Live from OpenRouter</p>
         </div>
         <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
            <div className="flex items-center gap-2 text-indigo-400 mb-1">
               <ShieldCheck className="h-4 w-4" />
               <span className="text-[10px] font-semibold uppercase tracking-wider">Active Agents</span>
            </div>
            <p className="text-2xl font-bold text-slate-100">{AGENTS.length}</p>
            <p className="text-[10px] text-slate-500">Extractors configured</p>
         </div>
         <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
            <div className="flex items-center gap-2 text-emerald-400 mb-1">
               <Zap className="h-4 w-4" />
               <span className="text-[10px] font-semibold uppercase tracking-wider">Default Model</span>
            </div>
            <p className="text-sm font-bold text-slate-200 truncate">Claude 3 Sonnet</p>
            <p className="text-[10px] text-slate-500">Highest reliability score</p>
         </div>
         <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
            <div className="flex items-center gap-2 text-amber-400 mb-1">
               <DollarSign className="h-4 w-4" />
               <span className="text-[10px] font-semibold uppercase tracking-wider">Est. Monthly Cost</span>
            </div>
            <p className="text-2xl font-bold text-slate-100">$42.30</p>
            <p className="text-[10px] text-slate-500">Across 180 runs</p>
         </div>
      </div>

      <div className="flex flex-1 gap-6 min-h-0">
        {/* Left - Agent Configuration */}
        <div className="w-[450px] overflow-y-auto rounded-xl border border-slate-800 bg-slate-900 flex flex-col shrink-0">
           <div className="border-b border-slate-800 p-4 shrink-0 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-slate-200">Agent Architectures</h2>
              <Settings2 className="h-4 w-4 text-slate-600" />
           </div>
           <div className="p-3 space-y-3 flex-1 overflow-y-auto scrollbar-hide">
              {AGENTS.map(agent => {
                const config = configs.find(c => c.agentId === agent.id);
                const active = selectedAgent === agent.id;
                return (
                  <button
                    key={agent.id}
                    onClick={() => setSelectedAgent(agent.id)}
                    className={`w-full rounded-xl p-4 text-left border transition-all ${
                      active ? 'bg-indigo-500/10 border-indigo-500/40' : 'bg-slate-950 border-slate-800 hover:border-slate-700 hover:bg-slate-900'
                    }`}
                  >
                    <div className="flex justify-between items-start mb-3">
                       <span className="text-xs font-semibold text-slate-300 uppercase tracking-widest">{agent.name}</span>
                       <span className="text-[9px] bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 px-1.5 py-0.5 rounded tracking-widest uppercase">{agent.type}</span>
                    </div>
                    
                    <div className="flex items-center gap-2 text-[10px] text-slate-400 mb-1.5 p-1.5 bg-slate-900 rounded-md border border-slate-800/50">
                       <Zap className="h-3 w-3 text-amber-500 shrink-0" />
                       <span className="font-bold flex-1">Primary:</span>
                       <span className="truncate text-slate-200 font-mono tracking-tight">{config?.primaryModel || "Awaiting Setup"}</span>
                    </div>
                    
                    {config?.fallbackModels && config.fallbackModels.length > 0 && (
                        <div className="mt-3">
                          <p className="text-[9px] text-slate-500 font-semibold uppercase tracking-wider mb-1.5 px-0.5">Enabled Fallback Pipeline</p>
                          <div className="flex gap-1.5 flex-wrap">
                             {config.fallbackModels.map((f, i) => (
                                 <span key={f} className="text-[9px] bg-slate-900 border border-slate-700/50 text-slate-300 pl-2 pr-1 py-1 rounded inline-flex items-center gap-1.5 font-mono shadow-sm">
                                    <span className="text-indigo-400">{i+1}.</span>
                                    {f.replace('/', '/\n').split('\n').pop() || f}
                                    <div 
                                      onClick={(e) => { e.stopPropagation(); removeFallback(agent.id, f); }} 
                                      className="ml-0.5 hover:bg-red-500/20 hover:text-red-400 rounded-full w-4 h-4 flex items-center justify-center cursor-pointer transition-colors"
                                    >
                                      ×
                                    </div>
                                 </span>
                             ))}
                          </div>
                        </div>
                    )}
                  </button>
                );
              })}
           </div>
        </div>

        {/* Right - Model Catalog */}
        <div className="flex-1 flex flex-col min-w-0">
           {/* Catalog Filters */}
           <div className="flex items-center gap-4 mb-4">
              <div className="relative flex-1">
                 <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                 <input 
                   type="text" 
                   placeholder="Search 180+ authoritative models (Anthropic, OpenAI, Google)..."
                   value={search}
                   onChange={(e) => setSearch(e.target.value)}
                   className="w-full bg-slate-900 border border-slate-800 rounded-lg pl-10 pr-4 py-2 flex-1 text-sm text-slate-200 outline-none focus:border-indigo-500/50"
                 />
              </div>
           </div>

           {/* Catalog List */}
           <div className="flex-1 overflow-y-auto rounded-xl border border-slate-800 bg-slate-900 scrollbar-hide relative overflow-hidden">
             {selectedAgent ? (
               <table className="w-full text-left text-sm relative z-10">
                  <thead className="sticky top-0 bg-slate-900 z-20 border-b border-slate-800 backdrop-blur-md">
                    <tr className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">
                       <th className="px-6 py-4">Authoritative Engine</th>
                       <th className="px-6 py-4 text-center">Context Window</th>
                       <th className="px-6 py-4 text-right">Pricing Analytics</th>
                       <th className="px-6 py-4 text-right">Routing Controls</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/50">
                     {filteredModels.map(model => (
                       <tr key={model.id} className="hover:bg-slate-800/30 group transition-colors">
                          <td className="px-6 py-4">
                              <div className="flex items-center gap-3">
                                 <div className="h-8 w-8 rounded bg-slate-950 border border-slate-800 shadow-sm flex items-center justify-center shrink-0">
                                    <Globe className="h-4 w-4 text-indigo-500/70" />
                                 </div>
                                 <div className="min-w-0">
                                    <p className="text-sm font-bold text-slate-200 truncate">{model.name}</p>
                                    <p className="text-[9px] text-slate-500 font-mono truncate">{model.id}</p>
                                 </div>
                              </div>
                          </td>
                          <td className="px-6 py-4 text-xs font-mono text-slate-400 text-center">
                             {(model.context_length / 1024).toFixed(0)}k
                          </td>
                          <td className="px-6 py-4 text-right font-mono">
                             <div className="space-y-1">
                                <p className="text-[10px] text-slate-400"><span className="text-slate-500 pr-2">PRMPT:</span> ${(parseFloat(model.pricing.prompt) * 1e6).toFixed(2)}</p>
                                <p className="text-[10px] text-slate-400"><span className="text-slate-500 pr-2">CPLTN:</span> ${(parseFloat(model.pricing.completion) * 1e6).toFixed(2)}</p>
                             </div>
                          </td>
                          <td className="px-6 py-4 text-right align-middle">
                              <div className="flex items-center gap-2 justify-end opacity-0 group-hover:opacity-100 transition-opacity">
                                <button 
                                  onClick={() => assignPrimary(selectedAgent, model.id)}
                                  className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-500/10 text-amber-500 hover:bg-amber-500 hover:text-slate-900 border border-amber-500/20 text-[10px] font-bold tracking-widest uppercase rounded shadow transition-all duration-300"
                                >
                                   Sets Primary <Zap className="h-3 w-3" />
                                </button>
                                <button 
                                  onClick={() => assignFallback(selectedAgent, model.id)}
                                  className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 text-slate-300 hover:bg-indigo-500 hover:text-white border border-slate-700 text-[10px] font-bold tracking-widest uppercase rounded shadow transition-all duration-300"
                                >
                                   Add Fallback <Layers className="h-3 w-3" />
                                </button>
                              </div>
                          </td>
                       </tr>
                     ))}
                  </tbody>
               </table>
             ) : (
                <div className="absolute inset-0 flex items-center justify-center flex-col text-slate-500">
                    <Layers className="h-12 w-12 text-slate-700 mb-4" />
                    <p className="font-bold tracking-wider uppercase text-sm">Select an Architecture</p>
                    <p className="text-xs text-slate-600 mt-1">Select an Agent to assign Primary & Fallback compute structures.</p>
                </div>
             )}
           </div>
        </div>
      </div>
    </div>
  );
}

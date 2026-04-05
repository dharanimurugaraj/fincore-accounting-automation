"use client";

export const dynamic = "force-dynamic";

import { useState, useEffect, useCallback } from "react";
import { 
  Calculator, 
  Save, 
  History, 
  CheckCircle, 
  AlertTriangle,
  RefreshCw,
  Edit3
} from "lucide-react";
import { api } from "@/lib/api";

interface Formula {
  id: string;
  name: string;
  description: string;
  expression: string;
  parameters: any;
  version: number;
  updatedAt: string;
  updatedBy: string;
}

export default function AdminFormulasPage() {
  const [formulas, setFormulas] = useState<Formula[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedFormula, setSelectedFormula] = useState<Formula | null>(null);
  const [editing, setEditing] = useState(false);
  const [newExpression, setNewExpression] = useState("");
  const [newParams, setNewParams] = useState("");
  const [history, setHistory] = useState<Formula[]>([]);
  const [showHistory, setShowHistory] = useState(false);

  const fetchFormulas = async () => {
    setLoading(true);
    try {
      const res = await api.get<{ formulas: Formula[] }>("admin/formulas");
      if (res && res.formulas) {
        setFormulas(res.formulas);
      }
    } catch (err) {
      console.error("Failed to fetch formulas:", err);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchFormulas();
  }, []);

  const handleSelect = (f: Formula) => {
    setSelectedFormula(f);
    setNewExpression(f.expression);
    setNewParams(JSON.stringify(f.parameters, null, 2));
    setEditing(false);
    setShowHistory(false);
  };

  const handleHistory = async (f: Formula) => {
    try {
      const res = await api.get<{ history: Formula[] }>(`admin/formulas/${f.name}/history`);
      if (res && res.history) {
        setHistory(res.history);
        setShowHistory(true);
      }
    } catch (err) {
      console.error("Failed to fetch history:", err);
    }
  };

  const saveFormula = async () => {
    if (!selectedFormula) return;
    try {
      let params = {};
      try { params = JSON.parse(newParams); } catch (e) { alert("Invalid Parameters JSON"); return; }
      
      const res = await api.post<{ status: string; version: number }>("admin/formulas", {
        name: selectedFormula.name,
        expression: newExpression,
        parameters: params,
        description: selectedFormula.description
      });
      
      if (res) {
        alert("Formula updated to version " + res.version);
        fetchFormulas();
        setEditing(false);
      }
    } catch (err) {
      console.error("Update failed:", err);
    }
  };

  return (
    <div className="flex h-[calc(100vh-12rem)] gap-6">
      {/* Sidebar - Formula List */}
      <div className="w-80 overflow-y-auto rounded-xl border border-slate-800 bg-slate-900">
        <div className="border-b border-slate-800 p-4">
          <h2 className="text-sm font-semibold text-slate-200">Core Formulas</h2>
        </div>
        <div className="p-2 space-y-1">
          {formulas.map((f) => (
            <button
              key={f.id}
              onClick={() => handleSelect(f)}
              className={`w-full rounded-lg p-3 text-left transition-colors ${
                selectedFormula?.id === f.id
                  ? "bg-indigo-500/10 text-indigo-400 border border-indigo-500/30"
                  : "text-slate-400 hover:bg-slate-800 hover:text-slate-200"
              }`}
            >
              <div className="flex items-center gap-2">
                <Calculator className="h-4 w-4" />
                <span className="text-sm font-medium">{f.name}</span>
              </div>
              <p className="mt-1 text-[10px] opacity-60 truncate">{f.description}</p>
              <div className="mt-2 flex items-center justify-between text-[10px]">
                <span className="rounded bg-slate-800 px-1 py-0.5 text-slate-500">v{f.version}</span>
                <span className="text-slate-500 italic">By {f.updatedBy}</span>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Main Panel - Editor/Details */}
      <div className="flex-1 overflow-y-auto rounded-xl border border-slate-800 bg-slate-900 p-6">
        {!selectedFormula ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <Calculator className="h-12 w-12 text-slate-700" />
            <h3 className="mt-4 text-slate-200 font-semibold">Select a formula to manage</h3>
            <p className="mt-2 text-sm text-slate-500">Admins can live-edit the logical definitions of core platform interest math here.</p>
          </div>
        ) : (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-slate-100">{selectedFormula.name}</h2>
                <p className="text-sm text-slate-500">{selectedFormula.description}</p>
              </div>
              <div className="flex items-center gap-3">
                 <button
                   onClick={() => handleHistory(selectedFormula)}
                   className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-700"
                 >
                   <History className="h-3.5 w-3.5" />
                   History
                 </button>
                 {!editing ? (
                   <button
                     onClick={() => setEditing(true)}
                     className="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-500"
                   >
                     <Edit3 className="h-3.5 w-3.5" />
                     Edit Formula
                   </button>
                 ) : (
                   <button
                     onClick={saveFormula}
                     className="flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-500"
                   >
                     <Save className="h-3.5 w-3.5" />
                     Save Version
                   </button>
                 )}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
               {/* Formula Expression */}
               <div className="space-y-3">
                 <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Logical Expression (Python)</h4>
                 <div className="relative">
                   <textarea
                     value={newExpression}
                     onChange={(e) => editing && setNewExpression(e.target.value)}
                     readOnly={!editing}
                     spellCheck={false}
                     className={`w-full h-32 rounded-lg border border-slate-800 bg-slate-950 p-4 font-mono text-sm leading-relaxed text-indigo-300 focus:border-indigo-500/50 outline-none ${!editing && 'opacity-60 cursor-not-allowed'}`}
                   />
                 </div>
               </div>

               {/* Default Parameters */}
               <div className="space-y-3">
                 <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Parameters (JSON)</h4>
                 <textarea
                   value={newParams}
                   onChange={(e) => editing && setNewParams(e.target.value)}
                   readOnly={!editing}
                   spellCheck={false}
                   className={`w-full h-32 rounded-lg border border-slate-800 bg-slate-950 p-4 font-mono text-sm leading-relaxed text-cyan-400 focus:border-cyan-500/50 outline-none ${!editing && 'opacity-60 cursor-not-allowed'}`}
                 />
               </div>
            </div>

            {/* Version History Modal/Overlay */}
            {showHistory && (
              <div className="mt-6 border-t border-slate-800 pt-6">
                 <h3 className="text-sm font-semibold text-slate-200 mb-4">Version History</h3>
                 <div className="space-y-2">
                    {history.map((h, i) => (
                      <div key={h.id} className={`flex items-center justify-between rounded-lg border border-slate-800 p-3 ${i === 0 ? 'bg-emerald-500/5 border-emerald-500/20' : 'bg-slate-900'}`}>
                         <div className="flex items-center gap-3">
                            <span className="text-xs font-mono text-slate-500">v{h.version}</span>
                            <span className="text-xs text-slate-200">{h.expression}</span>
                         </div>
                         <div className="text-right flex items-center gap-4">
                            <span className="text-xs text-slate-500 italic">By {h.updatedBy}</span>
                            <span className="text-[10px] text-slate-600 font-mono">{new Date(h.updatedAt).toLocaleDateString()}</span>
                            {i === 0 && <span className="text-[10px] bg-emerald-500/10 text-emerald-500 px-1.5 py-0.5 rounded">Active</span>}
                         </div>
                      </div>
                    ))}
                 </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

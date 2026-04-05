"use client";

import { useState, useEffect } from "react";
import { RefreshCw, Globe, AlertCircle, FileText } from "lucide-react";
import { api } from "@/lib/api";
import { formatINR } from "@/lib/utils";
import type { ForexTransaction } from "@/types";

export default function ForexPage() {
  const [data, setData] = useState<{ transactions: ForexTransaction[] }>({ transactions: [] });
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await api.get<{ transactions: ForexTransaction[] }>("forex");
      if (res && res.transactions) {
        setData({ transactions: res.transactions });
      }
    } catch (err) {
      console.error("Forex fetch failed:", err);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchData();
  }, []);

  const totalExcess = data.transactions.reduce((sum, t) => sum + (t.excessVsAvg || 0), 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Forex Register</h1>
          <p className="text-sm text-slate-400">
            Monitor import transactions and identify excess bank currency charges.
          </p>
        </div>
        <button
          onClick={fetchData}
          disabled={loading}
          className="flex items-center gap-1.5 rounded-lg border border-slate-800 bg-slate-900 px-3 py-1.5 text-sm text-slate-300 hover:bg-slate-800 disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="rounded-xl border border-red-500/30 bg-red-500/5 p-6">
          <p className="text-xs font-medium uppercase tracking-wider text-red-400">Total Excess Charges</p>
          <h2 className="mt-2 text-2xl font-bold text-slate-100">₹{formatINR(totalExcess)}</h2>
          <p className="mt-1 text-xs text-slate-500">Recoverable bank overcharges detected</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
          <p className="text-xs font-medium uppercase tracking-wider text-slate-500">Transactions Count</p>
          <h2 className="mt-2 text-2xl font-bold text-slate-100">{data.transactions.length}</h2>
          <p className="mt-1 text-xs text-slate-500">Processed this month</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-6 flex items-center justify-center">
            <button className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500">
              <FileText className="h-4 w-4" />
              Generate Dispute Letter
            </button>
        </div>
      </div>

      {!loading && data.transactions.length === 0 && (
        <div className="flex flex-col items-center justify-center rounded-xl border border-slate-800 bg-slate-900/50 p-12 text-center">
          <Globe className="h-12 w-12 text-slate-700" />
          <h2 className="mt-4 text-lg font-semibold text-slate-200">No transactions found</h2>
          <p className="mt-1 text-sm text-slate-500">
            Import transactions will appear here once identified from your remittance advices.
          </p>
        </div>
      )}

      {data.transactions.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-400">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-900/50 text-xs uppercase tracking-wider text-slate-500">
                  <th className="px-6 py-4 font-medium">BOE Date</th>
                  <th className="px-6 py-4 font-medium">Drawer/Ref</th>
                  <th className="px-6 py-4 font-medium text-right">FCY Amount</th>
                  <th className="px-6 py-4 font-medium text-center">Bank Rate</th>
                  <th className="px-6 py-4 font-medium text-right">INR Equivalent</th>
                  <th className="px-6 py-4 font-medium text-right">Excess Charge</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {data.transactions.map((t) => (
                  <tr key={t.id} className="hover:bg-slate-800/30">
                    <td className="px-6 py-4 text-xs text-slate-300">{t.valueDate}</td>
                    <td className="px-6 py-4">
                      <p className="text-sm font-medium text-slate-200">{t.drawerName}</p>
                      <p className="text-xs text-slate-500">{t.billReference}</p>
                    </td>
                    <td className="px-6 py-4 text-right tabular-nums text-slate-200">
                      {t.fcAmount.toLocaleString()} {t.currency}
                    </td>
                    <td className="px-6 py-4 text-center tabular-nums text-cyan-400">
                      {t.bankRate.toFixed(4)}
                    </td>
                    <td className="px-6 py-4 text-right font-medium text-slate-300">
                      ₹{formatINR(t.totalAmtINR)}
                    </td>
                    <td className="px-6 py-4 text-right">
                       <div className="flex items-center justify-end gap-1.5">
                         {t.excessVsAvg > 100 && <AlertCircle className="h-3.5 w-3.5 text-red-500" />}
                         <span className={t.excessVsAvg > 0 ? "font-semibold text-red-400" : "text-slate-500"}>
                           ₹{formatINR(t.excessVsAvg || 0)}
                         </span>
                       </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

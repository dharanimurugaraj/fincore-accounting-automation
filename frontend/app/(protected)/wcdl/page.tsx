"use client";

import { useState, useEffect } from "react";
import { RefreshCw, Calendar, AlertCircle } from "lucide-react";
import { api } from "@/lib/api";
import { formatINR } from "@/lib/utils";
import type { WCDLLoan } from "@/types";

export default function WCDLPage() {
  const [loans, setLoans] = useState<WCDLLoan[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchLoans = async () => {
    setLoading(true);
    try {
      const res = await api.get<{ loans: WCDLLoan[] }>("wcdl");
      if (res && res.loans) {
        setLoans(res.loans);
      }
    } catch (err) {
      console.error("WCDL fetch failed:", err);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchLoans();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-t-heading">WCDL Tracker</h1>
          <p className="text-sm text-t-muted">
            Track Working Capital Demand Loans — maturity dates, ROI, and interest.
          </p>
        </div>
        <button
          onClick={fetchLoans}
          disabled={loading}
          className="flex items-center gap-1.5 rounded-lg border border-neutral-border bg-neutral-card px-3 py-1.5 text-sm text-t-body hover:bg-neutral-row disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {!loading && loans.length === 0 && (
        <div className="flex flex-col items-center justify-center rounded-xl border border-neutral-border bg-neutral-card/50 p-12 text-center">
          <Calendar className="h-12 w-12 text-t-muted" />
          <h2 className="mt-4 text-lg font-semibold text-t-heading">No active loans found</h2>
          <p className="mt-1 text-sm text-t-muted">
            WCDL loans will appear here once identified from your advice letters.
          </p>
        </div>
      )}

      {loans.length > 0 && (
        <div className="grid grid-cols-1 gap-6">
          <div className="overflow-hidden rounded-xl border border-neutral-border bg-neutral-card">
            <div className="border-b border-neutral-border bg-neutral-card/50 px-6 py-4">
              <h3 className="text-sm font-semibold text-t-heading">Active & Historical Loans</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-neutral-border bg-neutral-card/30 text-xs uppercase tracking-wider text-t-muted">
                    <th className="px-6 py-3 font-medium">Loan No</th>
                    <th className="px-6 py-3 font-medium">Bank</th>
                    <th className="px-6 py-3 font-medium text-right">Principal</th>
                    <th className="px-6 py-3 font-medium text-center">ROI</th>
                    <th className="px-6 py-3 font-medium">Dates (Start - Mature)</th>
                    <th className="px-6 py-3 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-border">
                  {loans.map((loan) => (
                    <tr key={loan.id} className="hover:bg-neutral-row/30">
                      <td className="px-6 py-4 font-mono text-xs text-t-body">{loan.loanNumber}</td>
                      <td className="px-6 py-4 text-t-muted">{loan.bankName}</td>
                      <td className="px-6 py-4 text-right font-medium text-t-heading">₹{formatINR(loan.principal)}</td>
                      <td className="px-6 py-4 text-center text-primary">{(loan.roi * 100).toFixed(2)}%</td>
                      <td className="px-6 py-4 space-y-1">
                        <p className="text-xs text-t-body">{loan.startDate}</p>
                        <p className={`text-xs ${loan.status === 'ACTIVE' ? 'text-status-medium' : 'text-t-muted'}`}>
                          {loan.maturityDate}
                        </p>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${
                          loan.status === 'ACTIVE' 
                            ? 'bg-status-medium-bg text-status-medium' 
                            : 'bg-neutral-row text-t-muted'
                        }`}>
                          {loan.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <div className="rounded-xl border border-neutral-border bg-neutral-card p-6">
                <div className="flex items-center gap-2 mb-4">
                  <AlertCircle className="h-5 w-5 text-status-medium" />
                  <h3 className="text-sm font-semibold text-t-heading">Maturity Alerts</h3>
                </div>
                <div className="space-y-3">
                  {loans.filter(l => l.status === 'ACTIVE').map(loan => (
                    <div key={loan.id} className="rounded-lg bg-neutral-card/50 p-3 border border-neutral-border flex justify-between items-center">
                       <div>
                         <p className="text-sm text-t-body">{loan.loanNumber}</p>
                         <p className="text-xs text-t-muted">Matures: {loan.maturityDate}</p>
                       </div>
                       <div className="text-right">
                         <p className="text-sm font-semibold text-status-medium">₹{formatINR(loan.principal)}</p>
                       </div>
                    </div>
                  ))}
                </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

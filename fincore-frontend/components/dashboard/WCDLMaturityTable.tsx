"use client";

import type { WCDLLoan } from "@/types";

interface WCDLMaturityTableProps {
  loans: WCDLLoan[];
}

export default function WCDLMaturityTable({ loans }: WCDLMaturityTableProps) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
      <h3 className="text-sm font-semibold text-slate-200">WCDL Maturity Tracker</h3>
      <div className="mt-4 overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-slate-800 text-xs text-slate-400">
              <th className="pb-2 pr-4">Loan No.</th>
              <th className="pb-2 pr-4">Start</th>
              <th className="pb-2 pr-4">Maturity</th>
              <th className="pb-2 pr-4">Prepaid</th>
              <th className="pb-2 pr-4 text-right">Amount (Cr)</th>
              <th className="pb-2 pr-4 text-right">ROI</th>
              <th className="pb-2">Status</th>
            </tr>
          </thead>
          <tbody>
            {loans.map((loan) => (
              <tr
                key={loan.loanNumber}
                className="border-b border-slate-800/50 text-slate-300"
              >
                <td className="py-2.5 pr-4 font-mono text-xs">
                  {loan.loanNumber}
                </td>
                <td className="py-2.5 pr-4">{loan.startDate}</td>
                <td className="py-2.5 pr-4">{loan.maturityDate}</td>
                <td className="py-2.5 pr-4">
                  {loan.prepaymentDate || "—"}
                </td>
                <td className="py-2.5 pr-4 text-right">
                  {(loan.principal / 1e7).toFixed(0)}
                </td>
                <td className="py-2.5 pr-4 text-right">
                  {(loan.roi * 100).toFixed(2)}%
                </td>
                <td className="py-2.5">
                  <span
                    className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                      loan.status === "ACTIVE"
                        ? "bg-emerald-500/10 text-emerald-400"
                        : "bg-slate-700 text-slate-400"
                    }`}
                  >
                    {loan.status}
                    {loan.status === "ACTIVE" &&
                      loan.daysToMaturity !== undefined &&
                      ` — ${loan.daysToMaturity}d`}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

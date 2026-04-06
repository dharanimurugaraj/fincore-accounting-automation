"use client";

import type { WCDLLoan } from "@/types";

interface WCDLMaturityTableProps {
  loans: WCDLLoan[];
}

export default function WCDLMaturityTable({ loans }: WCDLMaturityTableProps) {
  return (
    <div className="rounded-xl border border-neutral-border bg-neutral-card p-6">
      <h3 className="text-sm font-semibold text-t-heading">WCDL Maturity Tracker</h3>
      <div className="mt-4 overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-neutral-border text-xs text-t-muted">
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
                className="border-b border-neutral-border/50 text-t-body"
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
                        ? "bg-status-success-bg text-status-success"
                        : "bg-neutral-border text-t-muted"
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

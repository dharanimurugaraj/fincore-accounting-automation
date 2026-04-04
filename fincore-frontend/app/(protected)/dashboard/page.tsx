"use client";

import { useState, useEffect } from "react";
import { RefreshCw, Calendar } from "lucide-react";
import KPICard from "@/components/dashboard/KPICard";
import UtilisationGauge from "@/components/dashboard/UtilisationGauge";
import TrendChart from "@/components/dashboard/TrendChart";
import WCDLMaturityTable from "@/components/dashboard/WCDLMaturityTable";
import { formatINR, formatCrores } from "@/lib/utils";
import { api } from "@/lib/api";
import type { KPI, TrendDataPoint, WCDLLoan } from "@/types";

interface DashboardData {
  month: string;
  kpis: KPI[];
  ccUtilisation: { actual: number; sanctioned: number };
  wcdlUtilisation: { actual: number; sanctioned: number };
  trendData: TrendDataPoint[];
  wcdlLoans: WCDLLoan[];
  chargesSummary: { penal: number; recurring: number; total: number };
  idleBalances: { account: string; avgBalance: number; loss: number }[];
}

const PLACEHOLDER_DATA: DashboardData = {
  month: "Feb-26",
  kpis: [
    {
      label: "Total CC Interest",
      value: `₹${formatINR(512205)}`,
      subtext: "Across all CC accounts",
      trend: "down",
      color: "text-emerald-400",
    },
    {
      label: "Total WCDL Interest",
      value: `₹${formatINR(3058904)}`,
      subtext: "3 active loans",
      trend: "up",
      color: "text-amber-400",
    },
    {
      label: "Finance Cost %",
      value: "7.43% p.a.",
      subtext: "Annualised, all instruments",
      trend: "flat",
      color: "text-cyan-400",
    },
    {
      label: "Total Bank Charges",
      value: `₹${formatINR(18540)}`,
      subtext: "₹4,200 penal charges",
      trend: "up",
      color: "text-red-400",
    },
    {
      label: "Avg CC Utilisation",
      value: `₹${formatCrores(138000000)} Cr`,
      subtext: "Daily average drawn balance",
      trend: "flat",
    },
    {
      label: "Idle Balance Loss",
      value: `₹${formatINR(12450)}`,
      subtext: "Notional opportunity cost",
      trend: "down",
      color: "text-amber-400",
    },
  ],
  ccUtilisation: { actual: 78.5, sanctioned: 100 },
  wcdlUtilisation: { actual: 62.3, sanctioned: 100 },
  trendData: [
    { month: "Sep-25", ccUtilisation: 12.8, financeCostPct: 7.62, wcdlUtilisation: 18.0 },
    { month: "Oct-25", ccUtilisation: 13.1, financeCostPct: 7.55, wcdlUtilisation: 20.5 },
    { month: "Nov-25", ccUtilisation: 13.5, financeCostPct: 7.48, wcdlUtilisation: 22.0 },
    { month: "Dec-25", ccUtilisation: 13.2, financeCostPct: 7.45, wcdlUtilisation: 19.5 },
    { month: "Jan-26", ccUtilisation: 13.6, financeCostPct: 7.44, wcdlUtilisation: 21.0 },
    { month: "Feb-26", ccUtilisation: 13.8, financeCostPct: 7.43, wcdlUtilisation: 20.0 },
  ],
  wcdlLoans: [
    {
      loanNumber: "240LN01260280020",
      startDate: "15-Jan-2026",
      maturityDate: "15-Apr-2026",
      principal: 250000000,
      roi: 0.0725,
      status: "ACTIVE",
      daysToMaturity: 17,
    },
    {
      loanNumber: "240LN01260340022",
      startDate: "03-Feb-2026",
      maturityDate: "03-May-2026",
      principal: 150000000,
      roi: 0.073,
      status: "ACTIVE",
      daysToMaturity: 35,
    },
    {
      loanNumber: "240LN01260180018",
      startDate: "20-Dec-2025",
      maturityDate: "20-Feb-2026",
      prepaymentDate: "12-Feb-2026",
      principal: 100000000,
      roi: 0.072,
      status: "CLOSED",
    },
  ],
  chargesSummary: { penal: 4200, recurring: 12340, total: 18540 },
  idleBalances: [
    { account: "HDFC-512 Current", avgBalance: 2450000, loss: 8320 },
    { account: "UBI Current", avgBalance: 1230000, loss: 4130 },
  ],
};

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData>(PLACEHOLDER_DATA);
  const [loading, setLoading] = useState(false);
  const [selectedMonth, setSelectedMonth] = useState("2026-02");

  const refreshData = async () => {
    setLoading(true);
    try {
      // Using our smart API helper which attaches the Auth token
      // The backend will now automatically identify "Bharadwaj R"
      const res = await api.get(`documents?month=${selectedMonth}`);
      if (res) {
        // Parse dynamic dashboard data if the backend provides it
        // setData(res as DashboardData);
      }
    } catch (err) {
      console.error("Dashboard refresh failed:", err);
    }
    setLoading(false);
  };

  useEffect(() => {
    refreshData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedMonth]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Dashboard</h1>
          <p className="text-sm text-slate-400">
            {data.month} — Working Capital Overview
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 rounded-lg border border-slate-800 bg-slate-900 px-3 py-1.5">
            <Calendar className="h-4 w-4 text-slate-500" />
            <input
              type="month"
              value={selectedMonth}
              onChange={(e) => setSelectedMonth(e.target.value)}
              className="bg-transparent text-sm text-slate-200 outline-none"
            />
          </div>
          <button
            onClick={refreshData}
            disabled={loading}
            className="flex items-center gap-1.5 rounded-lg border border-slate-800 bg-slate-900 px-3 py-1.5 text-sm text-slate-300 hover:bg-slate-800 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {data.kpis.map((kpi) => (
          <KPICard key={kpi.label} {...kpi} />
        ))}
      </div>

      {/* Utilisation Gauges */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <UtilisationGauge
          label="CC Utilisation (% of Sanctioned Limit)"
          actual={data.ccUtilisation.actual}
          sanctioned={data.ccUtilisation.sanctioned}
        />
        <UtilisationGauge
          label="WCDL Utilisation (% of Sanctioned Limit)"
          actual={data.wcdlUtilisation.actual}
          sanctioned={data.wcdlUtilisation.sanctioned}
        />
      </div>

      {/* Trend Chart + WCDL Table side by side */}
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <TrendChart data={data.trendData} />
        <WCDLMaturityTable loans={data.wcdlLoans} />
      </div>

      {/* Charges + Idle Balance sections */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Charges Breakdown */}
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
          <h3 className="text-sm font-semibold text-slate-200">Bank Charges Breakdown</h3>
          <div className="mt-4 space-y-3">
            {[
              { label: "Penal Charges", value: data.chargesSummary.penal, color: "text-red-400" },
              { label: "Recurring Charges", value: data.chargesSummary.recurring, color: "text-slate-300" },
              { label: "Total Charges", value: data.chargesSummary.total, color: "text-slate-100" },
            ].map((item) => (
              <div key={item.label} className="flex items-center justify-between border-b border-slate-800/50 pb-2">
                <span className="text-sm text-slate-400">{item.label}</span>
                <span className={`text-sm font-semibold ${item.color}`}>
                  ₹{formatINR(item.value)}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Idle Balance Losses */}
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
          <h3 className="text-sm font-semibold text-slate-200">Idle Balance — Notional Losses</h3>
          <div className="mt-4 space-y-3">
            {data.idleBalances.map((ib) => (
              <div key={ib.account} className="flex items-center justify-between border-b border-slate-800/50 pb-2">
                <div>
                  <p className="text-sm text-slate-300">{ib.account}</p>
                  <p className="text-xs text-slate-500">
                    Avg: ₹{formatINR(ib.avgBalance)}
                  </p>
                </div>
                <span className="text-sm font-semibold text-amber-400">
                  -₹{formatINR(ib.loss)}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

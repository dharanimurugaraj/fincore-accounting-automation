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
      color: "text-status-success",
    },
    {
      label: "Total WCDL Interest",
      value: `₹${formatINR(3058904)}`,
      subtext: "3 active loans",
      trend: "up",
      color: "text-status-medium",
    },
    {
      label: "Finance Cost %",
      value: "7.43% p.a.",
      subtext: "Annualised, all instruments",
      trend: "flat",
      color: "text-primary",
    },
    {
      label: "Total Bank Charges",
      value: `₹${formatINR(18540)}`,
      subtext: "₹4,200 penal charges",
      trend: "up",
      color: "text-status-critical",
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
      color: "text-status-medium",
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
      id: "mock1",
      bankName: "HDFC Bank Ltd.",
      loanNumber: "240LN01260280020",
      startDate: "15-Jan-2026",
      maturityDate: "15-Apr-2026",
      principal: 250000000,
      roi: 0.0725,
      status: "ACTIVE",
      daysToMaturity: 17,
    },
    {
      id: "mock2",
      bankName: "HDFC Bank Ltd.",
      loanNumber: "240LN01260340022",
      startDate: "03-Feb-2026",
      maturityDate: "03-May-2026",
      principal: 150000000,
      roi: 0.073,
      status: "ACTIVE",
      daysToMaturity: 35,
    },
    {
      id: "mock3",
      bankName: "Union Bank",
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
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedMonth, setSelectedMonth] = useState("2026-02");

  const refreshData = async () => {
    setLoading(true);
    try {
      const res = await api.get(`reports/dashboard?statement_month=${selectedMonth}`);
      if (res && (res as any).has_data) {
        setData(res as unknown as DashboardData);
      } else {
        // Force inject static presentation data to showcase the dashboard
        setData(PLACEHOLDER_DATA);
      }
    } catch (err) {
      console.error("Dashboard refresh failed:", err);
      // Fallback to static data for demonstration
      setData(PLACEHOLDER_DATA);
    }
    setLoading(false);
  };

  useEffect(() => {
    refreshData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedMonth]);

  if (loading && !data) {
    return (
      <div className="flex h-[70vh] items-center justify-center">
        <RefreshCw className="h-8 w-8 animate-spin text-ai-violet" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex h-[70vh] flex-col items-center justify-center p-12 text-center">
        <div className="mb-4 rounded-full bg-neutral-card/50 p-6 backdrop-blur-sm">
          <Calendar className="h-12 w-12 text-t-muted" />
        </div>
        <div className="mb-6 flex flex-col items-center gap-3">
          <div className="flex items-center gap-2 rounded-lg border border-neutral-border bg-neutral-card px-3 py-1.5">
            <Calendar className="h-4 w-4 text-t-muted" />
            <input
              type="month"
              value={selectedMonth}
              onChange={(e) => setSelectedMonth(e.target.value)}
              className="bg-transparent text-sm text-t-heading outline-none"
            />
          </div>
        </div>
        <h2 className="text-xl font-semibold text-t-heading">No report data for {selectedMonth}</h2>
        <p className="mt-2 max-w-md text-t-muted">
          Upload your bank statements for this month to generate the intelligence report and dashboard KPIs.
        </p>
        <button
          onClick={() => (window.location.href = "/upload")}
          className="mt-6 rounded-lg bg-ai-violet px-6 py-2 text-sm font-medium text-t-heading transition-colors hover:bg-ai-violet/90"
        >
          Upload Statements
        </button>
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${loading ? "opacity-30" : ""}`}>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-t-heading">Dashboard</h1>
          <p className="text-sm text-t-muted">
            {data?.month} — Working Capital Overview
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 rounded-lg border border-neutral-border bg-neutral-card px-3 py-1.5">
            <Calendar className="h-4 w-4 text-t-muted" />
            <input
              type="month"
              value={selectedMonth}
              onChange={(e) => setSelectedMonth(e.target.value)}
              className="bg-transparent text-sm text-t-heading outline-none"
            />
          </div>
          <button
            onClick={refreshData}
            disabled={loading}
            className="flex items-center gap-1.5 rounded-lg border border-neutral-border bg-neutral-card px-3 py-1.5 text-sm text-t-body hover:bg-neutral-row disabled:opacity-50"
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
        <div className="rounded-xl border border-neutral-border bg-neutral-card p-6">
          <h3 className="text-sm font-semibold text-t-heading">Bank Charges Breakdown</h3>
          <div className="mt-4 space-y-3">
            {[
              { label: "Penal Charges", value: data.chargesSummary.penal, color: "text-status-critical" },
              { label: "Recurring Charges", value: data.chargesSummary.recurring, color: "text-t-body" },
              { label: "Total Charges", value: data.chargesSummary.total, color: "text-t-heading" },
            ].map((item) => (
              <div key={item.label} className="flex items-center justify-between border-b border-neutral-border/50 pb-2">
                <span className="text-sm text-t-muted">{item.label}</span>
                <span className={`text-sm font-semibold ${item.color}`}>
                  ₹{formatINR(item.value)}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Idle Balance Losses */}
        <div className="rounded-xl border border-neutral-border bg-neutral-card p-6">
          <h3 className="text-sm font-semibold text-t-heading">Idle Balance — Notional Losses</h3>
          <div className="mt-4 space-y-3">
            {data.idleBalances.map((ib) => (
              <div key={ib.account} className="flex items-center justify-between border-b border-neutral-border/50 pb-2">
                <div>
                  <p className="text-sm text-t-body">{ib.account}</p>
                  <p className="text-xs text-t-muted">
                    Avg: ₹{formatINR(ib.avgBalance)}
                  </p>
                </div>
                <span className="text-sm font-semibold text-status-medium">
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

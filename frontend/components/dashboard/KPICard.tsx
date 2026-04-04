"use client";

import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import type { KPI } from "@/types";

export default function KPICard({ label, value, subtext, trend, color }: KPI) {
  const trendIcon =
    trend === "up" ? (
      <TrendingUp className="h-4 w-4 text-emerald-500" />
    ) : trend === "down" ? (
      <TrendingDown className="h-4 w-4 text-red-500" />
    ) : (
      <Minus className="h-4 w-4 text-slate-500" />
    );

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-400">{label}</p>
        {trend && trendIcon}
      </div>
      <p className={`mt-1 text-2xl font-bold ${color || "text-slate-100"}`}>
        {value}
      </p>
      {subtext && <p className="mt-1 text-xs text-slate-500">{subtext}</p>}
    </div>
  );
}

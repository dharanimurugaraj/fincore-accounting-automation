"use client";

import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import type { KPI } from "@/types";

export default function KPICard({ label, value, subtext, trend, color }: KPI) {
  const trendIcon =
    trend === "up" ? (
      <TrendingUp className="h-4 w-4 text-status-success" />
    ) : trend === "down" ? (
      <TrendingDown className="h-4 w-4 text-status-critical" />
    ) : (
      <Minus className="h-4 w-4 text-t-muted" />
    );

  return (
    <div className="rounded-xl border border-neutral-border bg-neutral-card p-6">
      <div className="flex items-center justify-between">
        <p className="text-sm text-t-muted">{label}</p>
        {trend && trendIcon}
      </div>
      <p className={`mt-1 text-2xl font-bold ${color || "text-t-heading"}`}>
        {value}
      </p>
      {subtext && <p className="mt-1 text-xs text-t-muted">{subtext}</p>}
    </div>
  );
}

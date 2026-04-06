"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import type { TrendDataPoint } from "@/types";

interface TrendChartProps {
  data: TrendDataPoint[];
}

export default function TrendChart({ data }: TrendChartProps) {
  return (
    <div className="rounded-xl border border-neutral-border bg-neutral-card p-6">
      <h3 className="text-sm font-semibold text-t-heading">
        6-Month Trend
      </h3>
      <div className="mt-4 h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="hsl(217, 33%, 17%)"
            />
            <XAxis
              dataKey="month"
              tick={{ fill: "#94a3b8", fontSize: 12 }}
              axisLine={{ stroke: "#334155" }}
            />
            <YAxis
              tick={{ fill: "#94a3b8", fontSize: 12 }}
              axisLine={{ stroke: "#334155" }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "#0f172a",
                border: "1px solid #334155",
                borderRadius: "8px",
                color: "#e2e8f0",
              }}
            />
            <Line
              type="monotone"
              dataKey="ccUtilisation"
              stroke="#06b6d4"
              strokeWidth={2}
              dot={{ r: 3, fill: "#06b6d4" }}
              name="CC Utilisation (Cr)"
            />
            <Line
              type="monotone"
              dataKey="financeCostPct"
              stroke="#f59e0b"
              strokeWidth={2}
              dot={{ r: 3, fill: "#f59e0b" }}
              name="Finance Cost %"
            />
            <Line
              type="monotone"
              dataKey="wcdlUtilisation"
              stroke="#10b981"
              strokeWidth={2}
              dot={{ r: 3, fill: "#10b981" }}
              name="WCDL Utilisation (Cr)"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

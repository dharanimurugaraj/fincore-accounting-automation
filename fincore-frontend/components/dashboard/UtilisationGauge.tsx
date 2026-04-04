"use client";

interface UtilisationGaugeProps {
  actual: number;
  sanctioned: number;
  label: string;
}

export default function UtilisationGauge({
  actual,
  sanctioned,
  label,
}: UtilisationGaugeProps) {
  const pct = Math.min((actual / sanctioned) * 100, 100);
  const isOver = actual > sanctioned;
  const color = isOver ? "text-red-400" : "text-emerald-400";
  const barColor = isOver ? "bg-red-500" : "bg-cyan-500";

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
      <p className="text-sm text-slate-400">{label}</p>
      <div className="mt-3 flex items-end gap-2">
        <span className={`text-3xl font-bold ${color}`}>
          {actual.toFixed(2)}%
        </span>
        <span className="pb-1 text-sm text-slate-500">
          / {sanctioned.toFixed(2)}% sanctioned
        </span>
      </div>
      <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-slate-800">
        <div
          className={`h-full rounded-full ${barColor} transition-all duration-500`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

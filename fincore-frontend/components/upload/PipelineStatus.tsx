"use client";

import { Check, Loader2, AlertTriangle, XCircle, Clock } from "lucide-react";
import type { RunStatus } from "@/types";

interface PipelineStatusProps {
  status: RunStatus;
  stage: number;
  errorMessage?: string;
}

const STAGE_LABELS: Record<string, string> = {
  PENDING: "Preparing pipeline...",
  STAGE1_RUNNING: "Stage 1: Extracting transactions from PDFs...",
  STAGE1_REVIEW: "Review required — low-confidence fields detected",
  STAGE2_RUNNING: "Stage 2: Building Working Sheet...",
  STAGE3_RUNNING: "Stage 3: Generating Banking Report...",
  VALIDATION_FAILED: "Validation failed — discrepancies found",
  AWAITING_APPROVAL: "Ready for approval — all checks passed",
  APPROVED: "Reports ready for download",
  FAILED: "Pipeline failed",
};

const STATUS_STYLES: Record<
  string,
  { icon: React.ReactNode; color: string }
> = {
  PENDING: {
    icon: <Clock className="h-5 w-5" />,
    color: "text-slate-400",
  },
  STAGE1_RUNNING: {
    icon: <Loader2 className="h-5 w-5 animate-spin" />,
    color: "text-cyan-400",
  },
  STAGE1_REVIEW: {
    icon: <AlertTriangle className="h-5 w-5" />,
    color: "text-amber-400",
  },
  STAGE2_RUNNING: {
    icon: <Loader2 className="h-5 w-5 animate-spin" />,
    color: "text-cyan-400",
  },
  STAGE3_RUNNING: {
    icon: <Loader2 className="h-5 w-5 animate-spin" />,
    color: "text-cyan-400",
  },
  VALIDATION_FAILED: {
    icon: <XCircle className="h-5 w-5" />,
    color: "text-red-400",
  },
  AWAITING_APPROVAL: {
    icon: <AlertTriangle className="h-5 w-5" />,
    color: "text-amber-400",
  },
  APPROVED: {
    icon: <Check className="h-5 w-5" />,
    color: "text-emerald-400",
  },
  FAILED: {
    icon: <XCircle className="h-5 w-5" />,
    color: "text-red-400",
  },
};

export default function PipelineStatus({
  status,
  stage,
  errorMessage,
}: PipelineStatusProps) {
  const style = STATUS_STYLES[status] || STATUS_STYLES.PENDING;

  const stages = [
    { num: 1, label: "Extract" },
    { num: 2, label: "Working Sheet" },
    { num: 3, label: "Report" },
    { num: 4, label: "Done" },
  ];

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
      <div className={`flex items-center gap-3 ${style.color}`}>
        {style.icon}
        <span className="text-sm font-medium">
          {STAGE_LABELS[status] || status}
        </span>
      </div>

      {errorMessage && (
        <p className="mt-2 text-xs text-red-400">{errorMessage}</p>
      )}

      <div className="mt-4 flex items-center gap-2">
        {stages.map((s) => (
          <div key={s.num} className="flex items-center gap-2">
            <div
              className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold ${
                stage >= s.num
                  ? "bg-cyan-500 text-slate-950"
                  : "bg-slate-800 text-slate-500"
              }`}
            >
              {stage > s.num ? (
                <Check className="h-3 w-3" />
              ) : (
                s.num
              )}
            </div>
            <span
              className={`text-xs ${
                stage >= s.num ? "text-slate-300" : "text-slate-600"
              }`}
            >
              {s.label}
            </span>
            {s.num < 4 && (
              <div
                className={`h-px w-8 ${
                  stage > s.num ? "bg-cyan-500" : "bg-slate-800"
                }`}
              />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

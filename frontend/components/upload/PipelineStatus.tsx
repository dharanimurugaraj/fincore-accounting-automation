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
    color: "text-t-muted",
  },
  STAGE1_RUNNING: {
    icon: <Loader2 className="h-5 w-5 animate-spin" />,
    color: "text-primary",
  },
  STAGE1_REVIEW: {
    icon: <AlertTriangle className="h-5 w-5" />,
    color: "text-status-medium",
  },
  STAGE2_RUNNING: {
    icon: <Loader2 className="h-5 w-5 animate-spin" />,
    color: "text-primary",
  },
  STAGE3_RUNNING: {
    icon: <Loader2 className="h-5 w-5 animate-spin" />,
    color: "text-primary",
  },
  VALIDATION_FAILED: {
    icon: <XCircle className="h-5 w-5" />,
    color: "text-status-critical",
  },
  AWAITING_APPROVAL: {
    icon: <AlertTriangle className="h-5 w-5" />,
    color: "text-status-medium",
  },
  APPROVED: {
    icon: <Check className="h-5 w-5" />,
    color: "text-status-success",
  },
  FAILED: {
    icon: <XCircle className="h-5 w-5" />,
    color: "text-status-critical",
  },
};

export default function PipelineStatus({
  status,
  stage,
  errorMessage,
}: PipelineStatusProps) {
  const style = STATUS_STYLES[status] || STATUS_STYLES.PENDING;

  const stages = [
    { num: 1, label: "Detecting Bank" },
    { num: 2, label: "Extracting Rows" },
    { num: 3, label: "Generating Sheets" },
    { num: 4, label: "Validation" },
    { num: 5, label: "Ready" },
  ];

  return (
    <div className="rounded-3xl border border-neutral-border bg-neutral-card/30 p-8 backdrop-blur-xl transition-all animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="flex items-start gap-4">
          <div className={`p-3 rounded-2xl bg-neutral-row/50 ${style.color}`}>
            {style.icon}
          </div>
          <div className="space-y-1">
            <h3 className="text-sm font-bold text-t-heading uppercase tracking-widest">{status.replace("_", " ")}</h3>
            <p className="text-sm text-t-body font-medium">
              {STAGE_LABELS[status] || status}
            </p>
            {errorMessage && (
              <p className="mt-1 text-xs text-status-critical font-medium bg-status-critical-bg/5 px-2 py-1 rounded inline-block">{errorMessage}</p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-1.5 md:gap-3 bg-neutral-app/30 p-2 rounded-2xl border border-neutral-border/50">
          {stages.map((s) => (
            <div key={s.num} className="flex items-center gap-1.5">
              <div
                className={`flex h-8 w-8 items-center justify-center rounded-xl text-xs font-bold transition-all duration-300 ${
                  stage >= s.num
                    ? "bg-primary shadow-[0_0_15px_rgba(255,191,0,0.3)] text-neutral-app"
                    : "bg-neutral-row text-t-muted"
                }`}
              >
                {stage > s.num ? (
                  <Check className="h-4 w-4" />
                ) : (
                  s.num
                )}
              </div>
              <span
                className={`text-[10px] font-bold uppercase tracking-wider hidden sm:inline-block ${
                  stage >= s.num ? "text-t-heading" : "text-t-muted"
                }`}
              >
                {s.label}
              </span>
              {s.num < 5 && (
                <div
                  className={`h-0.5 w-4 md:w-6 rounded-full transition-all duration-500 ${
                    stage > s.num ? "bg-primary" : "bg-neutral-row"
                  }`}
                />
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}


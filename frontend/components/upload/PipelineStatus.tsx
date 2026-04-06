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
    { num: 1, label: "Extract" },
    { num: 2, label: "Working Sheet" },
    { num: 3, label: "Report" },
    { num: 4, label: "Done" },
  ];

  return (
    <div className="rounded-xl border border-neutral-border bg-neutral-card p-6">
      <div className={`flex items-center gap-3 ${style.color}`}>
        {style.icon}
        <span className="text-sm font-medium">
          {STAGE_LABELS[status] || status}
        </span>
      </div>

      {errorMessage && (
        <p className="mt-2 text-xs text-status-critical">{errorMessage}</p>
      )}

      <div className="mt-4 flex items-center gap-2">
        {stages.map((s) => (
          <div key={s.num} className="flex items-center gap-2">
            <div
              className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold ${
                stage >= s.num
                  ? "bg-primary text-t-heading"
                  : "bg-neutral-row text-t-muted"
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
                stage >= s.num ? "text-t-body" : "text-t-muted"
              }`}
            >
              {s.label}
            </span>
            {s.num < 4 && (
              <div
                className={`h-px w-8 ${
                  stage > s.num ? "bg-primary" : "bg-neutral-row"
                }`}
              />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

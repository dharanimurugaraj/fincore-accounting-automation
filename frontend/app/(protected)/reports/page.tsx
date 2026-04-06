"use client";

import { useState, useEffect } from "react";
import {
  Download,
  FileSpreadsheet,
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
  Loader2,
  Eye,
} from "lucide-react";
import { api } from "@/lib/api";
import type { PipelineRun, RunStatus, ValidationCheck } from "@/types";

const STATUS_CONFIG: Record<
  RunStatus,
  { label: string; icon: React.ReactNode; classes: string }
> = {
  PENDING: {
    label: "Pending",
    icon: <Clock className="h-4 w-4" />,
    classes: "bg-neutral-border text-t-body",
  },
  STAGE1_RUNNING: {
    label: "Extracting",
    icon: <Loader2 className="h-4 w-4 animate-spin" />,
    classes: "bg-primary/10 text-primary",
  },
  STAGE1_REVIEW: {
    label: "Review",
    icon: <AlertTriangle className="h-4 w-4" />,
    classes: "bg-status-medium-bg text-status-medium",
  },
  STAGE2_RUNNING: {
    label: "Working Sheet",
    icon: <Loader2 className="h-4 w-4 animate-spin" />,
    classes: "bg-primary/10 text-primary",
  },
  STAGE3_RUNNING: {
    label: "Report",
    icon: <Loader2 className="h-4 w-4 animate-spin" />,
    classes: "bg-primary/10 text-primary",
  },
  VALIDATION_FAILED: {
    label: "Validation Failed",
    icon: <XCircle className="h-4 w-4" />,
    classes: "bg-red-500/10 text-status-critical",
  },
  AWAITING_APPROVAL: {
    label: "Awaiting Approval",
    icon: <AlertTriangle className="h-4 w-4" />,
    classes: "bg-status-medium-bg text-status-medium",
  },
  APPROVED: {
    label: "Approved",
    icon: <CheckCircle className="h-4 w-4" />,
    classes: "bg-status-success-bg text-status-success",
  },
  FAILED: {
    label: "Failed",
    icon: <XCircle className="h-4 w-4" />,
    classes: "bg-red-500/10 text-status-critical",
  },
};

const SAMPLE_RUNS: PipelineRun[] = [
  {
    runId: "run-001",
    statementMonth: "2026-02",
    status: "APPROVED",
    stage: 4,
    uploadCount: 5,
    statementExcelKey: "outputs/default-org/2026/02/statement_excel.xlsx",
    workingSheetKey: "outputs/default-org/2026/02/working_sheet.xlsx",
    bankingReportKey: "outputs/default-org/2026/02/banking_report.xlsx",
    validationResult: {
      passed: true,
      blocked: false,
      checks: [
        { name: "CC Interest — HDFC-521", computed: 28822.78, bank_stated: 28822.78, difference: 0, status: "PASS", tolerance: 1 },
        { name: "Balance Check — HDFC-521", computed: -138425196.92, bank_stated: -138425196.92, difference: 0, status: "PASS", tolerance: 1 },
        { name: "Forex INR — BOE-2026-001", computed: 8456230.00, bank_stated: 8456230.00, difference: 0, status: "PASS", tolerance: 1 },
      ],
      warnings: [],
    },
    startedAt: "2026-02-28T14:30:00Z",
    completedAt: "2026-02-28T14:35:22Z",
    createdAt: "2026-02-28T14:30:00Z",
  },
  {
    runId: "run-000",
    statementMonth: "2026-01",
    status: "APPROVED",
    stage: 4,
    uploadCount: 4,
    statementExcelKey: "outputs/default-org/2026/01/statement_excel.xlsx",
    workingSheetKey: "outputs/default-org/2026/01/working_sheet.xlsx",
    bankingReportKey: "outputs/default-org/2026/01/banking_report.xlsx",
    startedAt: "2026-01-31T10:00:00Z",
    completedAt: "2026-01-31T10:04:18Z",
    createdAt: "2026-01-31T10:00:00Z",
  },
];

export default function ReportsPage() {
  const [runs, setRuns] = useState<PipelineRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedRunId, setExpandedRunId] = useState<string | null>(null);

  const fetchRuns = async () => {
    setLoading(true);
    try {
      const data = await api.get<{ reports: PipelineRun[] }>("reports");
      if (data && data.reports) {
        setRuns(data.reports);
      }
    } catch (err) {
      console.error("Failed to fetch reports:", err);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchRuns();
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-t-heading">Reports</h1>
        <p className="text-sm text-t-muted">
          Generated banking reports and pipeline runs
        </p>
      </div>

      <div className="space-y-4">
        {runs.map((run) => {
          const config = STATUS_CONFIG[run.status];
          const expanded = expandedRunId === run.runId;
          const canDownload = run.status === "APPROVED";

          return (
            <div
              key={run.runId}
              className="overflow-hidden rounded-xl border border-neutral-border bg-neutral-card"
            >
              {/* Run Header */}
              <div className="flex items-center justify-between p-5">
                <div className="flex items-center gap-4">
                  <FileSpreadsheet className="h-8 w-8 text-t-muted" />
                  <div>
                    <h3 className="text-sm font-semibold text-t-heading">
                      Banking Report — {run.statementMonth}
                    </h3>
                    <p className="text-xs text-t-muted">
                      {run.uploadCount} PDF{run.uploadCount !== 1 ? "s" : ""} processed
                      {run.completedAt && (
                        <> &middot; Completed{" "}
                          {new Date(run.completedAt).toLocaleDateString("en-IN", {
                            day: "2-digit",
                            month: "short",
                            year: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </>
                      )}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <span
                    className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${config.classes}`}
                  >
                    {config.icon}
                    {config.label}
                  </span>

                  {run.validationResult && (
                    <button
                      onClick={() =>
                        setExpandedRunId(expanded ? null : run.runId)
                      }
                      className="flex items-center gap-1 rounded-lg border border-neutral-border px-2.5 py-1 text-xs text-t-muted hover:bg-neutral-row hover:text-t-heading"
                    >
                      <Eye className="h-3.5 w-3.5" />
                      Validation
                    </button>
                  )}
                </div>
              </div>

              {/* Download Links */}
              {canDownload && (
                <div className="border-t border-neutral-border bg-neutral-app/30 px-5 py-3">
                  <div className="flex flex-wrap gap-2">
                    {run.statementExcelKey && (
                      <a
                        href={`/api/documents?action=download&key=${encodeURIComponent(run.statementExcelKey)}`}
                        className="flex items-center gap-1.5 rounded-lg border border-neutral-border bg-neutral-row px-3 py-1.5 text-xs text-t-body hover:border-primary/50 hover:text-primary"
                      >
                        <Download className="h-3.5 w-3.5" />
                        Statement Excel
                      </a>
                    )}
                    {run.workingSheetKey && (
                      <a
                        href={`/api/documents?action=download&key=${encodeURIComponent(run.workingSheetKey)}`}
                        className="flex items-center gap-1.5 rounded-lg border border-neutral-border bg-neutral-row px-3 py-1.5 text-xs text-t-body hover:border-primary/50 hover:text-primary"
                      >
                        <Download className="h-3.5 w-3.5" />
                        Working Sheet
                      </a>
                    )}
                    {run.bankingReportKey && (
                      <a
                        href={`/api/documents?action=download&key=${encodeURIComponent(run.bankingReportKey)}`}
                        className="flex items-center gap-1.5 rounded-lg border border-neutral-border bg-neutral-row px-3 py-1.5 text-xs text-t-body hover:border-primary/50 hover:text-primary"
                      >
                        <Download className="h-3.5 w-3.5" />
                        Banking Report
                      </a>
                    )}
                  </div>
                </div>
              )}

              {/* Validation Details (expandable) */}
              {expanded && run.validationResult && (
                <div className="border-t border-neutral-border bg-neutral-app/50 p-5">
                  <h4 className="mb-3 text-xs font-semibold uppercase tracking-wide text-t-muted">
                    Validation Checks
                  </h4>
                  <div className="space-y-2">
                    {run.validationResult.checks.map((check, idx) => (
                      <ValidationRow key={idx} check={check} />
                    ))}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {runs.length === 0 && (
        <div className="rounded-xl border border-neutral-border bg-neutral-card p-12 text-center">
          <FileSpreadsheet className="mx-auto h-10 w-10 text-t-muted" />
          <p className="mt-3 text-sm text-t-muted">No reports generated yet</p>
          <p className="text-xs text-t-muted">
            Upload bank statements and run the pipeline to generate reports
          </p>
        </div>
      )}
    </div>
  );
}

function ValidationRow({ check }: { check: ValidationCheck }) {
  const statusColors = {
    PASS: "text-status-success",
    WARN: "text-status-medium",
    FAIL: "text-status-critical",
  };

  const statusIcons = {
    PASS: <CheckCircle className="h-4 w-4 text-status-success" />,
    WARN: <AlertTriangle className="h-4 w-4 text-status-medium" />,
    FAIL: <XCircle className="h-4 w-4 text-status-critical" />,
  };

  return (
    <div className="flex items-center justify-between rounded-lg border border-neutral-border bg-neutral-card px-4 py-2.5">
      <div className="flex items-center gap-2.5">
        {statusIcons[check.status]}
        <span className="text-sm text-t-body">{check.name}</span>
      </div>
      <div className="flex items-center gap-4 text-xs">
        <span className="text-t-muted">
          Computed: ₹{check.computed.toLocaleString("en-IN", { maximumFractionDigits: 2 })}
        </span>
        <span className="text-t-muted">
          Stated: ₹{check.bank_stated.toLocaleString("en-IN", { maximumFractionDigits: 2 })}
        </span>
        {check.difference > 0 && (
          <span className={statusColors[check.status]}>
            Diff: ₹{check.difference.toLocaleString("en-IN", { maximumFractionDigits: 2 })}
          </span>
        )}
      </div>
    </div>
  );
}

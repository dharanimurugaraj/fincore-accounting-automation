import { create } from "zustand";
import type { PipelineRun, FileToUpload, RunStatus } from "@/types";

interface PipelineState {
  files: FileToUpload[];
  statementMonth: string;
  currentRun: PipelineRun | null;
  isPolling: boolean;
  pollingInterval: NodeJS.Timeout | null;

  addFiles: (files: FileToUpload[]) => void;
  removeFile: (index: number) => void;
  updateFile: (index: number, updates: Partial<FileToUpload>) => void;
  setStatementMonth: (month: string) => void;
  setCurrentRun: (run: PipelineRun | null) => void;
  clearFiles: () => void;

  startPolling: (runId: string) => void;
  stopPolling: () => void;
}

const POLL_INTERVAL = 3000;

export const usePipelineStore = create<PipelineState>((set, get) => ({
  files: [],
  statementMonth: new Date().toISOString().slice(0, 7),
  currentRun: null,
  isPolling: false,
  pollingInterval: null,

  addFiles: (files) =>
    set((state) => ({ files: [...state.files, ...files] })),

  removeFile: (index) =>
    set((state) => ({
      files: state.files.filter((_, i) => i !== index),
    })),

  updateFile: (index, updates) =>
    set((state) => ({
      files: state.files.map((f, i) =>
        i === index ? { ...f, ...updates } : f
      ),
    })),

  setStatementMonth: (month) => set({ statementMonth: month }),

  setCurrentRun: (run) => set({ currentRun: run }),

  clearFiles: () => set({ files: [], currentRun: null }),

  startPolling: (runId: string) => {
    const { pollingInterval } = get();
    if (pollingInterval) clearInterval(pollingInterval);

    const poll = async () => {
      try {
        const res = await fetch(`/api/pipeline?runId=${runId}`);
        if (!res.ok) return;
        const raw = await res.json();

        const mapped: PipelineRun = {
          runId: raw.run_id || raw.runId || runId,
          statementMonth: raw.statement_month || raw.statementMonth || "",
          status: raw.status,
          stage: raw.stage ?? 0,
          uploadCount: raw.upload_count || raw.uploadCount || 0,
          statementExcelKey: raw.statement_excel_key || raw.statementExcelKey,
          workingSheetKey: raw.working_sheet_key || raw.workingSheetKey,
          bankingReportKey: raw.banking_report_key || raw.bankingReportKey,
          validationResult: raw.validation_result || raw.validationResult,
          errorMessage: raw.error_message || raw.errorMessage,
          startedAt: raw.started_at || raw.startedAt,
          completedAt: raw.completed_at || raw.completedAt,
          createdAt: raw.created_at || raw.createdAt || "",
          reviewFields: raw.review_fields || raw.reviewFields,
        };

        set({ currentRun: mapped });

        const terminalStatuses: RunStatus[] = [
          "APPROVED",
          "FAILED",
          "VALIDATION_FAILED",
          "AWAITING_APPROVAL",
          "STAGE1_REVIEW",
        ];
        if (terminalStatuses.includes(mapped.status)) {
          get().stopPolling();
        }
      } catch {
        // Silently retry on next interval
      }
    };

    poll();
    const interval = setInterval(poll, POLL_INTERVAL);
    set({ isPolling: true, pollingInterval: interval });
  },

  stopPolling: () => {
    const { pollingInterval } = get();
    if (pollingInterval) clearInterval(pollingInterval);
    set({ isPolling: false, pollingInterval: null });
  },
}));

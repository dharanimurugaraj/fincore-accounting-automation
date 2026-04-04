"use client";

import { useState, useCallback } from "react";
import { Play, Trash2, Download, CheckCircle } from "lucide-react";
import DropZone from "@/components/upload/DropZone";
import FileCard from "@/components/upload/FileCard";
import PipelineStatus from "@/components/upload/PipelineStatus";
import { usePipelineStore } from "@/store/pipeline.store";
import type { FileToUpload, RunStatus } from "@/types";

function detectAccountFromFilename(name: string): {
  bankName: string;
  accountType: string;
  accountId: string;
  detected: boolean;
} {
  const lower = name.toLowerCase();
  let bankName = "Unknown";
  let accountType = "Unknown";
  let accountId = "";

  if (/hdfc/i.test(lower)) bankName = "HDFC";
  else if (/ubi|union/i.test(lower)) bankName = "UBI";
  else if (/sbi|state\s*bank/i.test(lower)) bankName = "SBI";
  else if (/icici/i.test(lower)) bankName = "ICICI";
  else if (/axis/i.test(lower)) bankName = "AXIS";

  if (/cc|cash.?credit/i.test(lower)) accountType = "CC";
  else if (/current|ca\b/i.test(lower)) accountType = "Current";
  else if (/wcdl|demand.?loan/i.test(lower)) accountType = "WCDL";
  else if (/forex|remittance|import/i.test(lower)) accountType = "Forex";
  else if (/savings|sb\b/i.test(lower)) accountType = "Savings";

  const numbers = name.match(/\d{3,}/);
  if (numbers) accountId = numbers[0];

  const detected = bankName !== "Unknown" || accountType !== "Unknown";
  return { bankName, accountType, accountId, detected };
}

export default function UploadPage() {
  const {
    files,
    addFiles,
    removeFile,
    updateFile,
    statementMonth,
    setStatementMonth,
    currentRun,
    clearFiles,
    startPolling,
  } = usePipelineStore();

  const [isUploading, setIsUploading] = useState(false);

  const handleFilesSelected = useCallback(
    (selectedFiles: File[]) => {
      const fileEntries: FileToUpload[] = selectedFiles.map((f) => {
        const detection = detectAccountFromFilename(f.name);
        return {
          file: f,
          filename: f.name,
          bankName: detection.bankName,
          accountType: detection.accountType,
          accountId: detection.accountId,
          detectedFrom: detection.detected ? "filename" : "manual",
          uploading: false,
          uploaded: false,
        };
      });
      addFiles(fileEntries);
    },
    [addFiles]
  );

  const handleUpdateAccount = useCallback(
    (index: number, bankName: string, accountType: string, accountId: string) => {
      updateFile(index, { bankName, accountType, accountId, detectedFrom: "manual" });
    },
    [updateFile]
  );

  const uploadAndRunPipeline = async () => {
    if (files.length === 0) return;
    setIsUploading(true);

    const orgId = "default-org";

    try {
      const formData = new FormData();
      formData.append("org_id", orgId);
      formData.append("statement_month", statementMonth);

      for (const f of files) {
        formData.append("files", f.file);
      }

      for (let i = 0; i < files.length; i++) {
        updateFile(i, { uploading: true });
      }

      const uploadRes = await fetch("/api/upload", {
        method: "POST",
        body: formData,
      });

      if (!uploadRes.ok) throw new Error("File upload failed");
      const uploadData = await uploadRes.json();
      const s3Keys: string[] = uploadData.uploads.map(
        (u: { s3_key: string }) => u.s3_key
      );

      for (let i = 0; i < files.length; i++) {
        const key = s3Keys[i] || "";
        updateFile(i, { uploading: false, uploaded: true, s3Key: key });
      }

      if (s3Keys.length > 0) {
        const runRes = await fetch("/api/pipeline", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            org_id: orgId,
            statement_month: statementMonth,
            pdf_s3_keys: s3Keys,
          }),
        });

        if (runRes.ok) {
          const runData = await runRes.json();
          startPolling(runData.run_id);
        }
      }
    } catch (err) {
      for (let i = 0; i < files.length; i++) {
        updateFile(i, {
          uploading: false,
          error: err instanceof Error ? err.message : "Upload failed",
        });
      }
    }

    setIsUploading(false);
  };

  const allUploaded = files.length > 0 && files.every((f) => f.uploaded);
  const pipelineActive = currentRun && !["APPROVED", "FAILED"].includes(currentRun.status);
  const pipelineDone = currentRun?.status === "APPROVED";
  const canDownload = pipelineDone && currentRun;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Upload Statements</h1>
          <p className="text-sm text-slate-400">
            Upload bank statement PDFs to start the processing pipeline
          </p>
        </div>
        <div className="flex items-center gap-3">
          <label className="text-sm text-slate-400">Statement Month</label>
          <input
            type="month"
            value={statementMonth}
            onChange={(e) => setStatementMonth(e.target.value)}
            className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-200 outline-none focus:border-cyan-500/50"
            disabled={isUploading || !!pipelineActive}
          />
        </div>
      </div>

      {!pipelineActive && !pipelineDone && (
        <DropZone
          onFilesSelected={handleFilesSelected}
          disabled={isUploading}
        />
      )}

      {files.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-200">
              {files.length} file{files.length > 1 ? "s" : ""} selected
            </h2>
            {!pipelineActive && !pipelineDone && (
              <button
                onClick={clearFiles}
                className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-red-400"
              >
                <Trash2 className="h-3.5 w-3.5" />
                Clear all
              </button>
            )}
          </div>

          {files.map((file, index) => (
            <FileCard
              key={`${file.filename}-${index}`}
              file={file}
              index={index}
              onRemove={removeFile}
              onUpdateAccount={handleUpdateAccount}
            />
          ))}
        </div>
      )}

      {files.length > 0 && !currentRun && (
        <button
          onClick={uploadAndRunPipeline}
          disabled={isUploading || files.length === 0}
          className="flex items-center gap-2 rounded-lg bg-cyan-500 px-6 py-2.5 text-sm font-semibold text-slate-950 transition-colors hover:bg-cyan-400 disabled:opacity-50"
        >
          <Play className="h-4 w-4" />
          {isUploading ? "Uploading..." : "Upload & Run Pipeline"}
        </button>
      )}

      {currentRun && (
        <PipelineStatus
          status={currentRun.status}
          stage={currentRun.stage}
          errorMessage={currentRun.errorMessage}
        />
      )}

      {currentRun?.status === "STAGE1_REVIEW" && currentRun.reviewFields && (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-6">
          <h3 className="text-sm font-semibold text-amber-400">
            Review Required — Low Confidence Fields
          </h3>
          <div className="mt-3 space-y-2">
            {currentRun.reviewFields.map((rf, i) => (
              <div key={i} className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-900 p-3">
                <div>
                  <p className="text-sm text-slate-200">{rf.account}</p>
                  <p className="text-xs text-slate-500">{rf.file}</p>
                </div>
                <span className="rounded-full bg-amber-500/10 px-2.5 py-0.5 text-xs font-medium text-amber-400">
                  {(rf.confidence * 100).toFixed(0)}% confidence
                </span>
              </div>
            ))}
          </div>
          <button
            onClick={async () => {
              await fetch("/api/pipeline", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  action: "confirm",
                  run_id: currentRun.runId,
                }),
              });
              startPolling(currentRun.runId);
            }}
            className="mt-4 rounded-lg bg-amber-500 px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-amber-400"
          >
            Confirm & Continue
          </button>
        </div>
      )}

      {currentRun?.status === "AWAITING_APPROVAL" && (
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/5 p-6">
          <div className="flex items-center gap-2">
            <CheckCircle className="h-5 w-5 text-emerald-400" />
            <h3 className="text-sm font-semibold text-emerald-400">
              Validation Passed — Ready for Approval
            </h3>
          </div>
          {currentRun.validationResult && (
            <div className="mt-3 grid grid-cols-3 gap-4 text-center">
              <div className="rounded-lg bg-slate-900 p-3">
                <p className="text-2xl font-bold text-emerald-400">
                  {currentRun.validationResult.checks.filter((c) => c.status === "PASS").length}
                </p>
                <p className="text-xs text-slate-500">Passed</p>
              </div>
              <div className="rounded-lg bg-slate-900 p-3">
                <p className="text-2xl font-bold text-amber-400">
                  {currentRun.validationResult.warnings.length}
                </p>
                <p className="text-xs text-slate-500">Warnings</p>
              </div>
              <div className="rounded-lg bg-slate-900 p-3">
                <p className="text-2xl font-bold text-red-400">
                  {currentRun.validationResult.checks.filter((c) => c.status === "FAIL").length}
                </p>
                <p className="text-xs text-slate-500">Failed</p>
              </div>
            </div>
          )}
          <button
            onClick={async () => {
              await fetch("/api/pipeline", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  action: "approve",
                  run_id: currentRun.runId,
                }),
              });
              startPolling(currentRun.runId);
            }}
            className="mt-4 rounded-lg bg-emerald-500 px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-emerald-400"
          >
            Approve & Finalize
          </button>
        </div>
      )}

      {canDownload && (
        <div className="rounded-xl border border-cyan-500/30 bg-cyan-500/5 p-6">
          <h3 className="mb-4 text-sm font-semibold text-cyan-400">
            Reports Ready for Download
          </h3>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {currentRun.statementExcelKey && (
              <a
                href={`/api/documents?action=download&key=${encodeURIComponent(currentRun.statementExcelKey)}`}
                className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800 p-4 text-sm text-slate-200 hover:border-cyan-500/50 hover:bg-slate-700"
              >
                <Download className="h-4 w-4 text-cyan-400" />
                Statement Excel
              </a>
            )}
            {currentRun.workingSheetKey && (
              <a
                href={`/api/documents?action=download&key=${encodeURIComponent(currentRun.workingSheetKey)}`}
                className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800 p-4 text-sm text-slate-200 hover:border-cyan-500/50 hover:bg-slate-700"
              >
                <Download className="h-4 w-4 text-cyan-400" />
                Working Sheet
              </a>
            )}
            {currentRun.bankingReportKey && (
              <a
                href={`/api/documents?action=download&key=${encodeURIComponent(currentRun.bankingReportKey)}`}
                className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800 p-4 text-sm text-slate-200 hover:border-cyan-500/50 hover:bg-slate-700"
              >
                <Download className="h-4 w-4 text-cyan-400" />
                Banking Report
              </a>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

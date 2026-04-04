"use client";

import { FileText, X, Check, Loader2, AlertTriangle } from "lucide-react";
import type { FileToUpload } from "@/types";

interface FileCardProps {
  file: FileToUpload;
  index: number;
  onRemove: (index: number) => void;
  onUpdateAccount: (
    index: number,
    bankName: string,
    accountType: string,
    accountId: string
  ) => void;
}

export default function FileCard({
  file,
  index,
  onRemove,
  onUpdateAccount,
}: FileCardProps) {
  const statusIcon = file.uploaded ? (
    <Check className="h-4 w-4 text-emerald-500" />
  ) : file.uploading ? (
    <Loader2 className="h-4 w-4 animate-spin text-cyan-500" />
  ) : file.error ? (
    <AlertTriangle className="h-4 w-4 text-red-500" />
  ) : null;

  const sizeKB = (file.file.size / 1024).toFixed(0);

  return (
    <div className="flex items-center gap-4 rounded-lg border border-slate-800 bg-slate-900 p-4">
      <FileText className="h-8 w-8 shrink-0 text-slate-500" />

      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-slate-200">
          {file.filename}
        </p>
        <p className="text-xs text-slate-500">
          {sizeKB} KB &middot; {file.bankName} &middot; {file.accountType} &middot;{" "}
          {file.accountId}
          {file.detectedFrom === "filename" && (
            <span className="ml-1 text-cyan-500">(auto-detected)</span>
          )}
        </p>
      </div>

      <div className="flex items-center gap-2">
        {statusIcon}
        {!file.uploading && !file.uploaded && (
          <button
            onClick={() => onRemove(index)}
            className="rounded p-1 text-slate-500 hover:bg-slate-800 hover:text-slate-300"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  );
}

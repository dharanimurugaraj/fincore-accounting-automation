"use client";

import { useCallback } from "react";
import { Upload } from "lucide-react";

interface DropZoneProps {
  onFilesSelected: (files: File[]) => void;
  disabled?: boolean;
}

export default function DropZone({ onFilesSelected, disabled }: DropZoneProps) {
  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      if (disabled) return;
      const files = Array.from(e.dataTransfer.files).filter(
        (f) => f.type === "application/pdf"
      );
      if (files.length > 0) onFilesSelected(files);
    },
    [onFilesSelected, disabled]
  );

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (disabled || !e.target.files) return;
      const files = Array.from(e.target.files);
      if (files.length > 0) onFilesSelected(files);
    },
    [onFilesSelected, disabled]
  );

  return (
    <div
      onDrop={handleDrop}
      onDragOver={(e) => e.preventDefault()}
      className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-12 transition-colors ${
        disabled
          ? "border-neutral-border bg-neutral-card/30"
          : "border-neutral-border bg-neutral-card/50 hover:border-primary/50 hover:bg-neutral-card"
      }`}
    >
      <Upload className="mb-4 h-10 w-10 text-t-muted" />
      <p className="text-sm font-medium text-t-body">
        Drag & drop bank statement PDFs here
      </p>
      <p className="mt-1 text-xs text-t-muted">PDF only, max 20MB each</p>
      <label className="mt-4 cursor-pointer rounded-lg bg-neutral-row px-4 py-2 text-sm text-t-body transition-colors hover:bg-neutral-border">
        Browse Files
        <input
          type="file"
          multiple
          accept=".pdf"
          className="hidden"
          onChange={handleFileInput}
          disabled={disabled}
        />
      </label>
    </div>
  );
}

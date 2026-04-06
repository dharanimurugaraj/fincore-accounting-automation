"use client";

import { useState, useEffect } from "react";
import { FileText, Download, Search, Filter, RefreshCw } from "lucide-react";
import { formatINR } from "@/lib/utils";
import { api } from "@/lib/api";
import type { UploadedFile, UploadStatus } from "@/types";

const STATUS_BADGE: Record<UploadStatus, { label: string; classes: string }> = {
  UPLOADED: { label: "Uploaded", classes: "bg-neutral-border text-t-body" },
  OCR_RUNNING: { label: "Processing", classes: "bg-primary/10 text-primary" },
  OCR_COMPLETE: { label: "Complete", classes: "bg-status-success-bg text-status-success" },
  OCR_FAILED: { label: "Failed", classes: "bg-red-500/10 text-status-critical" },
  NEEDS_REVIEW: { label: "Review", classes: "bg-status-medium-bg text-status-medium" },
};

const SAMPLE_DOCS: UploadedFile[] = [
  {
    id: "1",
    filename: "HDFC_521_CC_Feb2026.pdf",
    s3Key: "uploads/default-org/2026/02/HDFC_521_CC_Feb2026.pdf",
    bankName: "HDFC",
    accountType: "CC",
    accountId: "521",
    statementMonth: "2026-02",
    fileSizeBytes: 245760,
    status: "OCR_COMPLETE",
    createdAt: "2026-02-28T10:30:00Z",
  },
  {
    id: "2",
    filename: "HDFC_512_Current_Feb2026.pdf",
    s3Key: "uploads/default-org/2026/02/HDFC_512_Current_Feb2026.pdf",
    bankName: "HDFC",
    accountType: "Current",
    accountId: "512",
    statementMonth: "2026-02",
    fileSizeBytes: 189400,
    status: "OCR_COMPLETE",
    createdAt: "2026-02-28T10:31:00Z",
  },
  {
    id: "3",
    filename: "UBI_Current_Feb2026.pdf",
    s3Key: "uploads/default-org/2026/02/UBI_Current_Feb2026.pdf",
    bankName: "UBI",
    accountType: "Current",
    accountId: "CA-4321",
    statementMonth: "2026-02",
    fileSizeBytes: 312000,
    status: "OCR_COMPLETE",
    createdAt: "2026-02-28T10:32:00Z",
  },
  {
    id: "4",
    filename: "WCDL_Advice_Feb2026.pdf",
    s3Key: "uploads/default-org/2026/02/WCDL_Advice_Feb2026.pdf",
    bankName: "HDFC",
    accountType: "WCDL",
    accountId: "WCDL",
    statementMonth: "2026-02",
    fileSizeBytes: 98000,
    status: "OCR_COMPLETE",
    createdAt: "2026-02-28T10:33:00Z",
  },
  {
    id: "5",
    filename: "Forex_Remittance_Feb2026.pdf",
    s3Key: "uploads/default-org/2026/02/Forex_Remittance_Feb2026.pdf",
    bankName: "HDFC",
    accountType: "Forex",
    accountId: "FOREX",
    statementMonth: "2026-02",
    fileSizeBytes: 156000,
    status: "NEEDS_REVIEW",
    createdAt: "2026-02-28T10:34:00Z",
  },
];

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<UploadedFile[]>(SAMPLE_DOCS);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterStatus, setFilterStatus] = useState<string>("all");

  const fetchDocuments = async () => {
    setLoading(true);
    try {
      const data = await api.get<{ documents: UploadedFile[] }>(`documents`);
      if (data && data.documents) {
        setDocuments(data.documents);
      }
    } catch (err) {
      console.error("Failed to fetch documents:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  const filtered = documents.filter((doc) => {
    const matchesSearch =
      searchQuery === "" ||
      doc.filename.toLowerCase().includes(searchQuery.toLowerCase()) ||
      doc.bankName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      doc.accountType.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = filterStatus === "all" || doc.status === filterStatus;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-t-heading">Documents</h1>
          <p className="text-sm text-t-muted">
            All uploaded statements — {documents.length} document{documents.length !== 1 ? "s" : ""}
          </p>
        </div>
        <button
          onClick={fetchDocuments}
          disabled={loading}
          className="flex items-center gap-1.5 rounded-lg border border-neutral-border bg-neutral-card px-3 py-1.5 text-sm text-t-body hover:bg-neutral-row"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-t-muted" />
          <input
            type="text"
            placeholder="Search by filename, bank, or account type..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="h-9 w-full rounded-lg border border-neutral-border bg-neutral-card pl-10 pr-4 text-sm text-t-heading placeholder-slate-500 outline-none focus:border-primary/50"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-t-muted" />
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="h-9 rounded-lg border border-neutral-border bg-neutral-card px-3 text-sm text-t-heading outline-none focus:border-primary/50"
          >
            <option value="all">All Statuses</option>
            <option value="UPLOADED">Uploaded</option>
            <option value="OCR_RUNNING">Processing</option>
            <option value="OCR_COMPLETE">Complete</option>
            <option value="OCR_FAILED">Failed</option>
            <option value="NEEDS_REVIEW">Needs Review</option>
          </select>
        </div>
      </div>

      {/* Documents Table */}
      <div className="overflow-hidden rounded-xl border border-neutral-border bg-neutral-card">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-neutral-border bg-neutral-app/50">
              <th className="px-4 py-3 text-xs font-medium text-t-muted">Filename</th>
              <th className="px-4 py-3 text-xs font-medium text-t-muted">Bank</th>
              <th className="px-4 py-3 text-xs font-medium text-t-muted">Account</th>
              <th className="px-4 py-3 text-xs font-medium text-t-muted">Month</th>
              <th className="px-4 py-3 text-xs font-medium text-t-muted">Size</th>
              <th className="px-4 py-3 text-xs font-medium text-t-muted">Status</th>
              <th className="px-4 py-3 text-xs font-medium text-t-muted">Uploaded</th>
              <th className="px-4 py-3 text-xs font-medium text-t-muted"></th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((doc, idx) => (
              <tr
                key={doc.id}
                className={`border-b border-neutral-border/50 transition-colors hover:bg-neutral-row/30 ${
                  idx % 2 === 0 ? "bg-neutral-card" : "bg-neutral-app/30"
                }`}
              >
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4 shrink-0 text-t-muted" />
                    <span className="truncate text-t-heading">{doc.filename}</span>
                  </div>
                </td>
                <td className="px-4 py-3 text-t-body">{doc.bankName}</td>
                <td className="px-4 py-3">
                  <span className="rounded bg-neutral-row px-1.5 py-0.5 text-xs text-t-body">
                    {doc.accountType}
                  </span>
                  {doc.accountId && (
                    <span className="ml-1 text-xs text-t-muted">{doc.accountId}</span>
                  )}
                </td>
                <td className="px-4 py-3 text-t-muted">{doc.statementMonth}</td>
                <td className="px-4 py-3 text-t-muted">
                  {(doc.fileSizeBytes / 1024).toFixed(0)} KB
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                      STATUS_BADGE[doc.status]?.classes || "bg-neutral-border text-t-body"
                    }`}
                  >
                    {STATUS_BADGE[doc.status]?.label || doc.status}
                  </span>
                </td>
                <td className="px-4 py-3 text-xs text-t-muted">
                  {new Date(doc.createdAt).toLocaleDateString("en-IN", {
                    day: "2-digit",
                    month: "short",
                    year: "numeric",
                  })}
                </td>
                <td className="px-4 py-3">
                  <button
                    className="rounded p-1.5 text-t-muted hover:bg-neutral-row hover:text-primary"
                    title="Download original"
                  >
                    <Download className="h-4 w-4" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {filtered.length === 0 && (
          <div className="p-12 text-center">
            <FileText className="mx-auto h-10 w-10 text-t-muted" />
            <p className="mt-3 text-sm text-t-muted">No documents found</p>
            <p className="text-xs text-t-muted">
              {searchQuery ? "Try a different search term" : "Upload bank statements to get started"}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

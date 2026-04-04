export type Role = "ADMIN" | "ANALYST" | "VIEWER";

export type UploadStatus =
  | "UPLOADED"
  | "OCR_RUNNING"
  | "OCR_COMPLETE"
  | "OCR_FAILED"
  | "NEEDS_REVIEW";

export type RunStatus =
  | "PENDING"
  | "STAGE1_RUNNING"
  | "STAGE1_REVIEW"
  | "STAGE2_RUNNING"
  | "STAGE3_RUNNING"
  | "VALIDATION_FAILED"
  | "AWAITING_APPROVAL"
  | "APPROVED"
  | "FAILED";

export interface UploadedFile {
  id: string;
  filename: string;
  s3Key: string;
  bankName: string;
  accountType: string;
  accountId: string;
  statementMonth: string;
  fileSizeBytes: number;
  status: UploadStatus;
  createdAt: string;
}

export interface PipelineRun {
  runId: string;
  statementMonth: string;
  status: RunStatus;
  stage: number;
  uploadCount: number;
  statementExcelKey?: string;
  workingSheetKey?: string;
  bankingReportKey?: string;
  validationResult?: ValidationResult;
  errorMessage?: string;
  startedAt?: string;
  completedAt?: string;
  createdAt: string;
  reviewFields?: ReviewField[];
}

export interface ReviewField {
  file: string;
  account: string;
  confidence: number;
  data?: Record<string, unknown>;
}

export interface ValidationCheck {
  name: string;
  computed: number;
  bank_stated: number;
  difference: number;
  status: "PASS" | "WARN" | "FAIL";
  tolerance: number;
}

export interface ValidationResult {
  passed: boolean;
  blocked: boolean;
  checks: ValidationCheck[];
  warnings: ValidationCheck[];
}

export interface KPI {
  label: string;
  value: string;
  subtext?: string;
  trend?: "up" | "down" | "flat";
  color?: string;
}

export interface WCDLLoan {
  loanNumber: string;
  startDate: string;
  maturityDate: string;
  prepaymentDate?: string;
  principal: number;
  roi: number;
  status: "ACTIVE" | "CLOSED";
  daysToMaturity?: number;
}

export interface IdleBalanceLoss {
  account: string;
  avgBalance: number;
  days: number;
  notionalLoss: number;
}

export interface TrendDataPoint {
  month: string;
  ccUtilisation: number;
  financeCostPct: number;
  wcdlUtilisation: number;
}

export interface ForexTransaction {
  srNo: number;
  boeDate: string;
  valueDate: string;
  drawerName: string;
  billReference: string;
  currency: string;
  fcAmount: number;
  bankRate: number;
  marketAvgRate: number;
  excessVsAvg: number;
  excessVsHigh: number;
  billAmtINR: number;
  billCommission: number;
  swiftCharges: number;
  totalAmtINR: number;
}

export interface FileToUpload {
  file: File;
  filename: string;
  bankName: string;
  accountType: string;
  accountId: string;
  detectedFrom: "filename" | "manual";
  uploading: boolean;
  uploaded: boolean;
  error?: string;
  s3Key?: string;
  uploadId?: string;
}

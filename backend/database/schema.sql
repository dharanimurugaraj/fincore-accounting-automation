-- FinCore Database Schema
-- Optimized for Firebase Google Auth and Dynamic Engagement

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Roles Table (Numeric RBAC)
-- 0: SUPER_ADMIN, 1: ADMIN, 2: ANALYST, 3: VIEWER
CREATE TABLE IF NOT EXISTS "Role" (
    id             SERIAL PRIMARY KEY,
    name           TEXT UNIQUE NOT NULL,
    description    TEXT,
    "allowedPages" TEXT[] DEFAULT '{"*"}'
);

INSERT INTO "Role" (id, name, description, "allowedPages") VALUES 
(0, 'SUPER_ADMIN', 'Platform-wide total access', '{"*"}'),
(1, 'ADMIN', 'Organization-level administration', '{"*"}'),
(2, 'ANALYST', 'Standard organization user', '{"Dashboard", "Upload", "Documents", "Reports", "WCDL Tracker", "Forex Register", "Activity"}'),
(3, 'VIEWER', 'Read-only organization access', '{"Dashboard", "Reports"}'),
(4, 'PENDING_APPROVAL', 'User awaiting administrator confirmation', '{}')
ON CONFLICT (id) DO UPDATE SET 
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    "allowedPages" = EXCLUDED."allowedPages";

-- Enums
DO $$ BEGIN
    CREATE TYPE "UploadStatus" AS ENUM ('UPLOADED', 'OCR_RUNNING', 'OCR_COMPLETE', 'OCR_FAILED', 'NEEDS_REVIEW');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE "RunStatus" AS ENUM ('PENDING', 'STAGE1_RUNNING', 'STAGE1_REVIEW', 'STAGE2_RUNNING', 'STAGE3_RUNNING', 'VALIDATION_FAILED', 'AWAITING_APPROVAL', 'APPROVED', 'FAILED');
EXCEPTION WHEN duplicate_object THEN null; END $$;

-- Tables
CREATE TABLE IF NOT EXISTS "Organisation" (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    "legalName" TEXT,
    "address" TEXT,
    "logoUrl" TEXT,
    "departments" TEXT[] DEFAULT '{}',
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "Customer" (
    id TEXT PRIMARY KEY,
    "customId" TEXT UNIQUE NOT NULL,
    "companyName" TEXT NOT NULL,
    "contactName" TEXT NOT NULL,
    "pan" TEXT NOT NULL,
    "cin" TEXT,
    "email" TEXT,
    "phone" TEXT,
    "industry" TEXT,
    "address" TEXT,
    "tags" TEXT[] DEFAULT '{}',
    "status" TEXT DEFAULT 'ACTIVE',
    "risk" TEXT DEFAULT 'LOW',
    "orgId" TEXT NOT NULL REFERENCES "Organisation"(id) ON DELETE CASCADE,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "User" (
    id           TEXT PRIMARY KEY,
    email        TEXT UNIQUE NOT NULL,
    name         TEXT,
    title        TEXT,
    phone        TEXT,
    "photoUrl"   TEXT,
    "roleId"     INTEGER NOT NULL DEFAULT 2 REFERENCES "Role"(id),
    "orgId"      TEXT NOT NULL REFERENCES "Organisation"(id) ON DELETE CASCADE,
    "firebaseUid" TEXT UNIQUE,
    theme        TEXT DEFAULT 'dark',
    timezone     TEXT DEFAULT 'UTC',
    "dateFormat" TEXT DEFAULT 'MM/DD/YYYY',
    "emailAlerts" BOOLEAN DEFAULT TRUE,
    "lastLogin"  TIMESTAMP WITH TIME ZONE,
    "createdAt"  TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "PipelineRun" (
    id TEXT PRIMARY KEY,
    "orgId" TEXT NOT NULL REFERENCES "Organisation"(id) ON DELETE CASCADE,
    "statementMonth" TEXT NOT NULL,
    status "RunStatus" DEFAULT 'PENDING',
    stage INTEGER DEFAULT 0,
    "statementExcelKey" TEXT,
    "workingSheetKey" TEXT,
    "bankingReportKey" TEXT,
    "validationResult" TEXT,
    "errorMessage" TEXT,
    "reportSummary" TEXT,
    "checksum" TEXT,
    "startedAt" TIMESTAMP WITH TIME ZONE,
    "completedAt" TIMESTAMP WITH TIME ZONE,
    "customerId" TEXT REFERENCES "Customer"(id) ON DELETE SET NULL,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "Upload" (
    id               TEXT PRIMARY KEY,
    "orgId"          TEXT NOT NULL REFERENCES "Organisation"(id) ON DELETE CASCADE,
    "uploadedById"   TEXT NOT NULL REFERENCES "User"(id) ON DELETE SET NULL,
    filename         TEXT NOT NULL,
    "s3Key"          TEXT UNIQUE NOT NULL,
    "bankName"       TEXT,
    "accountType"    TEXT,
    "accountId"      TEXT,
    "statementMonth" TEXT,
    "fileSizeBytes"  BIGINT,
    status "UploadStatus" DEFAULT 'UPLOADED',
    "runId"          TEXT REFERENCES "PipelineRun"(id) ON DELETE SET NULL,
    "customerId"     TEXT REFERENCES "Customer"(id) ON DELETE SET NULL,
    "createdAt"      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "WCDLLoan" (
    id                TEXT PRIMARY KEY,
    "orgId"           TEXT NOT NULL REFERENCES "Organisation"(id) ON DELETE CASCADE,
    "runId"           TEXT REFERENCES "PipelineRun"(id) ON DELETE SET NULL,
    "statementMonth"  TEXT NOT NULL,
    "loanNumber"      TEXT NOT NULL,
    "bankName"        TEXT NOT NULL,
    "principalAmount" NUMERIC(15, 2) NOT NULL,
    "roi"             NUMERIC(8, 6) NOT NULL,
    "startDate"       DATE NOT NULL,
    "maturityDate"    DATE NOT NULL,
    "prepaymentDate"  DATE,
    "status"          TEXT DEFAULT 'ACTIVE',
    "customerId"      TEXT REFERENCES "Customer"(id) ON DELETE SET NULL,
    "createdAt"       TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "updatedAt"       TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "ForexTransaction" (
    id TEXT PRIMARY KEY,
    "orgId" TEXT NOT NULL REFERENCES "Organisation"(id) ON DELETE CASCADE,
    "runId" TEXT REFERENCES "PipelineRun"(id) ON DELETE SET NULL,
    "statementMonth" TEXT NOT NULL,
    "srNo" INTEGER,
    "boeDate" DATE,
    "valueDate" DATE,
    "drawerName" TEXT,
    "billReference" TEXT,
    currency TEXT,
    "fcAmount" NUMERIC(18, 4),
    "bankRate" NUMERIC(10, 4),
    "marketAvgRate" NUMERIC(10, 4),
    "dayHighRate" NUMERIC(10, 4),
    "excessVsAvg" NUMERIC(18, 2),
    "excessVsHigh" NUMERIC(18, 2),
    "billAmtINR" NUMERIC(18, 2),
    "billCommission" NUMERIC(18, 2),
    "swiftCharges" NUMERIC(18, 2),
    "totalAmtINR" NUMERIC(18, 2),
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- AI Configuration (Managed by Admins)
CREATE TABLE IF NOT EXISTS "AgentConfig" (
    id               TEXT PRIMARY KEY,
    "orgId"          TEXT NOT NULL REFERENCES "Organisation"(id),
    "agentId"        TEXT NOT NULL,
    "primaryModel"   TEXT NOT NULL,
    "fallbackModels" TEXT[],
    "maxRetries"     INTEGER DEFAULT 3,
    "temperature"    NUMERIC(3, 2) DEFAULT 0.0,
    "updatedAt"      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE("orgId", "agentId")
);

-- AI Usage Logs (For Activity Rendering)
CREATE TABLE IF NOT EXISTS "AIUsageLog" (
    id TEXT PRIMARY KEY,
    "userId" TEXT NOT NULL REFERENCES "User"(id) ON DELETE CASCADE,
    "userEmail" TEXT NOT NULL,
    "orgId" TEXT NOT NULL REFERENCES "Organisation"(id) ON DELETE CASCADE,
    model TEXT NOT NULL,
    "tokensIn" INTEGER DEFAULT 0,
    "tokensOut" INTEGER DEFAULT 0,
    "costUsd" NUMERIC(15, 6) DEFAULT 0.0,
    action TEXT,
    "sessionId" TEXT,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Audit Logs (Immutable history)
CREATE TABLE IF NOT EXISTS "AuditLog" (
    id           TEXT PRIMARY KEY,
    "orgId"      TEXT NOT NULL REFERENCES "Organisation"(id) ON DELETE CASCADE,
    "userId"     TEXT REFERENCES "User"(id) ON DELETE SET NULL,
    action       TEXT NOT NULL,
    "entityType" TEXT NOT NULL,
    "entityId"   TEXT NOT NULL,
    metadata     JSONB,
    "createdAt"  TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Human Approvals
CREATE TABLE IF NOT EXISTS "Approval" (
    id           TEXT PRIMARY KEY,
    "runId"      TEXT NOT NULL REFERENCES "PipelineRun"(id) ON DELETE CASCADE,
    "userId"     TEXT NOT NULL REFERENCES "User"(id) ON DELETE CASCADE,
    "createdAt"  TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Formulas (Managed by Admins)
CREATE TABLE IF NOT EXISTS "FormulaConfiguration" (
    id          TEXT PRIMARY KEY,
    "orgId"     TEXT NOT NULL REFERENCES "Organisation"(id),
    name        TEXT NOT NULL,
    version     INTEGER NOT NULL,
    expression  TEXT NOT NULL,
    parameters  JSONB,
    description TEXT,
    "isActive"  BOOLEAN DEFAULT TRUE,
    "updatedAt" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Seed Initial Organisation
INSERT INTO "Organisation" (id, name) VALUES ('default-org', 'Vyrenzo Bank Demo') ON CONFLICT DO NOTHING;

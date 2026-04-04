-- FinCore Database Schema
-- Optimized for Firebase Google Auth and Dynamic Engagement

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enums
DO $$ BEGIN
    CREATE TYPE "Role" AS ENUM ('ADMIN', 'ANALYST', 'VIEWER');
EXCEPTION WHEN duplicate_object THEN null; END $$;

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
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "User" (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    "photoUrl" TEXT,
    role "Role" DEFAULT 'ANALYST',
    "orgId" TEXT NOT NULL REFERENCES "Organisation"(id) ON DELETE CASCADE,
    "firebaseUid" TEXT UNIQUE,
    "lastLogin" TIMESTAMP WITH TIME ZONE,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
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
    "startedAt" TIMESTAMP WITH TIME ZONE,
    "completedAt" TIMESTAMP WITH TIME ZONE,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "Upload" (
    id TEXT PRIMARY KEY,
    "orgId" TEXT NOT NULL REFERENCES "Organisation"(id) ON DELETE CASCADE,
    "uploadedById" TEXT NOT NULL REFERENCES "User"(id) ON DELETE SET NULL,
    filename TEXT NOT NULL,
    "s3Key" TEXT UNIQUE NOT NULL,
    "bankName" TEXT,
    "accountType" TEXT,
    "accountId" TEXT,
    "statementMonth" TEXT,
    "fileSizeBytes" BIGINT,
    status "UploadStatus" DEFAULT 'UPLOADED',
    "runId" TEXT REFERENCES "PipelineRun"(id) ON DELETE SET NULL,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "Approval" (
    id TEXT PRIMARY KEY,
    "runId" TEXT NOT NULL REFERENCES "PipelineRun"(id) ON DELETE CASCADE,
    "userId" TEXT NOT NULL REFERENCES "User"(id) ON DELETE CASCADE,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "AuditLog" (
    id TEXT PRIMARY KEY,
    "orgId" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    action TEXT NOT NULL,
    "entityType" TEXT NOT NULL,
    "entityId" TEXT NOT NULL,
    metadata TEXT,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Seed Initial Organisation
INSERT INTO "Organisation" (id, name) VALUES ('default-org', 'Vyrenzo Bank Demo') ON CONFLICT DO NOTHING;

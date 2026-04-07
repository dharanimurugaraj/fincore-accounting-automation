-- backend/sql/fix_schema.sql
ALTER TABLE "PipelineRun" ADD COLUMN IF NOT EXISTS "metadata" JSONB;
ALTER TABLE "PipelineRun" ADD COLUMN IF NOT EXISTS "updatedAt" TIMESTAMP DEFAULT NOW();

-- SCHEMA FIX: Ensure all tables have consistent customerId columns 
-- This matches the schema.prisma production expectations.

ALTER TABLE "Upload" ADD COLUMN IF NOT EXISTS "customerId" TEXT REFERENCES "Customer"(id);
ALTER TABLE "WCDLLoan" ADD COLUMN IF NOT EXISTS "customerId" TEXT REFERENCES "Customer"(id);
ALTER TABLE "PipelineRun" ADD COLUMN IF NOT EXISTS "customerId" TEXT REFERENCES "Customer"(id);

-- Verify and log
DO $$ 
BEGIN 
    RAISE NOTICE 'Schema fix applied successfully for customerId columns.';
END $$;

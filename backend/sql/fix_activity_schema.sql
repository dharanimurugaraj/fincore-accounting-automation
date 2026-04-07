-- AI Activity Schema Fix
-- Adds the missing orgId column to enable company-wide tracking for Admin roles

-- [1] Add the column if it doesn't exist
ALTER TABLE "AIUsageLog" ADD COLUMN IF NOT EXISTS "orgId" TEXT REFERENCES "Organisation"(id) ON DELETE SET NULL;

-- [2] Optional: If you had previous data, you could populate it here if userId mapped correctly to an org.
-- For now, new actions will automatically capture it from the Chat API.

-- Verify the table structure
\d "AIUsageLog"

-- Permissions Harmonization Script
-- Updates all system roles to use the new granular module strings (Resource:Action)

-- [1] SUPER_ADMIN: Universal Access
UPDATE "Role" SET "allowedPages" = '{"*"}' WHERE id = 0 OR name = 'SUPER_ADMIN';

-- [2] ADMIN: High-Level Organization Access (Full Platform)
UPDATE "Role" SET "allowedPages" = '{
    "Dashboard:read", "Dashboard:write", 
    "Customers:read", "Customers:write", 
    "Upload:read", "Upload:write", 
    "Documents:read", "Documents:write", 
    "Reports:read", "Reports:write", 
    "WCDL:read", "WCDL:write", 
    "Forex:read", "Forex:write", 
    "Activity:read", "Audit:read"
}' WHERE id = 1 OR name = 'ADMIN';

-- [3] ANALYST (Example for Role 2): Limited Access
UPDATE "Role" SET "allowedPages" = '{
    "Dashboard:read", 
    "Customers:read", 
    "Documents:read", 
    "Reports:read", 
    "Activity:read"
}' WHERE id = 2 OR name = 'ANALYST';

-- Verify results
SELECT id, name, "allowedPages" FROM "Role" ORDER BY id ASC;

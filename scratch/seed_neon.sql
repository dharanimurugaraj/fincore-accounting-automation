-- Seed Roles
INSERT INTO "Role" (id, name, description, "allowedPages") VALUES 
(0, 'Super Admin', 'Full platform access', ARRAY['*']),
(1, 'Admin', 'Organization management', ARRAY['*']),
(2, 'Analyst', 'Data processing access', ARRAY['dashboard', 'upload', 'reports']),
(3, 'Viewer', 'Read-only access', ARRAY['dashboard', 'reports']),
(4, 'New User', 'Pending role assignment', ARRAY['home'])
ON CONFLICT (id) DO NOTHING;

-- Create Default Organisation
INSERT INTO "Organisation" (id, name, "createdAt") 
VALUES ('org_default', 'Vyrenzo Default', NOW())
ON CONFLICT (id) DO NOTHING;

-- Create/Elevate User
INSERT INTO "User" (id, email, "roleId", "orgId", "createdAt")
VALUES ('user_superadmin', 'bharad.vyrenzo@gmail.com', 0, 'org_default', NOW())
ON CONFLICT (email) DO UPDATE SET "roleId" = 0;

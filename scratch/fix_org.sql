INSERT INTO "Organisation" (id, name, "createdAt") 
VALUES ('default-org', 'Vyrenzo Org', NOW())
ON CONFLICT (id) DO NOTHING;

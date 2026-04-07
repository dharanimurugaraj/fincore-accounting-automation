// prisma.config.ts
import "dotenv/config";
import { defineConfig } from "prisma/config";

// Detect DATABASE_URL from any available source
const dbUrl = process.env.DATABASE_URL || "postgresql://localhost:5432/fincore_dev";

export default defineConfig({
  schema: "prisma/schema.prisma",
  datasource: {
    url: dbUrl,
  },
});

// prisma.config.ts
import { defineConfig } from "@prisma/config";

/**
 * Prisma 7 Configuration
 * In Prisma 7, connection strings are managed here instead of schema.prisma.
 */
export default defineConfig({
  schema: "prisma/schema.prisma",
  datasource: {
    // Falls back to direct string if env variable is missing
    url: process.env.DATABASE_URL || "postgresql://localhost:5432/fincore_dev",
  },
});

"use server";

import { PrismaClient } from "@prisma/client";
import { PrismaPg } from "@prisma/adapter-pg";
import { Pool } from "pg";

const globalForPrisma = global as unknown as { prisma: PrismaClient };

// Correct way to initialize Prisma 7 with a PostgreSQL Driver Adapter
const connectionString = process.env.DATABASE_URL;

if (!connectionString) {
  console.error("❌ CRITICAL: DATABASE_URL is missing in environment variables.");
}

const pool = new Pool({ connectionString });
const adapter = new PrismaPg(pool);

const prismaClientOptions = {
  adapter,
  log: process.env.NODE_ENV === "development" ? ["query", "error", "warn"] : ["error"],
};

export const prisma = (() => {
  try {
    if (!connectionString) throw new Error("DATABASE_URL is missing");
    return globalForPrisma.prisma || new PrismaClient(prismaClientOptions);
  } catch (error) {
    console.error("🔥 DATABASE_INIT_ERROR:", error);
    // Return a proxy that throws on any access to alert the developer
    return new Proxy({} as PrismaClient, {
      get: () => { throw new Error("Database not initialized. Check server logs."); }
    });
  }
})();

if (process.env.NODE_ENV !== "production") globalForPrisma.prisma = prisma;

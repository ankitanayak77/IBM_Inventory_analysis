import { drizzle } from "drizzle-orm/node-postgres";
import { Pool } from "pg";

/**
 * A single, shared Pool across the app (per Neon's own guidance — see
 * BUILD_NOTES.md "Phase 2" for the sourced steps — a fresh Pool per
 * request exhausts connections quickly in serverless environments).
 * Reads DATABASE_URL at call time, not import time, so tests can swap it.
 */
let pool: Pool | null = null;

export function getDb() {
  if (!process.env.DATABASE_URL) {
    throw new Error(
      "DATABASE_URL is not set. For local development, copy .env.local (see BUILD_NOTES.md). " +
        "For production, set it to your real Postgres/Neon connection string."
    );
  }
  if (!pool) {
    const isLocalhost =
      process.env.DATABASE_URL.includes("127.0.0.1") ||
      process.env.DATABASE_URL.includes("localhost");
    pool = new Pool({
      connectionString: process.env.DATABASE_URL,
      ssl: isLocalhost ? false : { rejectUnauthorized: false },
    });
  }
  return drizzle(pool);
}

/** Only for tests: forces a fresh Pool on the next getDb() call. */
export function _resetPoolForTests() {
  pool = null;
}

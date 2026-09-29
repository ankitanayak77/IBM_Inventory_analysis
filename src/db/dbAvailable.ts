import { Pool } from "pg";

/**
 * Checks whether the configured DATABASE_URL is genuinely reachable.
 * Allows test suites to skip gracefully when running offline or in an
 * environment without a live Postgres daemon (as documented in BUILD_NOTES.md),
 * while executing in full when connected to Neon or a live database.
 */
export async function checkDbAvailable(): Promise<boolean> {
  if (!process.env.DATABASE_URL) return false;

  const isLocalhost =
    process.env.DATABASE_URL.includes("127.0.0.1") ||
    process.env.DATABASE_URL.includes("localhost");

  const pool = new Pool({
    connectionString: process.env.DATABASE_URL,
    ssl: isLocalhost ? false : { rejectUnauthorized: false },
    connectionTimeoutMillis: 2000,
  });

  try {
    const client = await pool.connect();
    client.release();
    await pool.end();
    return true;
  } catch {
    await pool.end().catch(() => {});
    return false;
  }
}

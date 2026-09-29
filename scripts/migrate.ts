import { config } from "dotenv";
config({ path: ".env.local" });
import { drizzle } from "drizzle-orm/node-postgres";
import { migrate } from "drizzle-orm/node-postgres/migrator";
import { Pool } from "pg";

async function main() {
  if (!process.env.DATABASE_URL) {
    throw new Error("DATABASE_URL is not set. Copy .env.local (local dev) or set your real connection string.");
  }

  const isLocalhost =
    process.env.DATABASE_URL.includes("127.0.0.1") ||
    process.env.DATABASE_URL.includes("localhost");

  const pool = new Pool({
    connectionString: process.env.DATABASE_URL,
    ssl: isLocalhost ? false : { rejectUnauthorized: false },
  });

  const db = drizzle(pool);
  const masked = process.env.DATABASE_URL.replace(/:[^:@]+@/, ":***@");
  console.log("Running migrations against:", masked);

  try {
    await migrate(db, { migrationsFolder: "./drizzle/migrations" });
    console.log("✓ Migrations complete.");
  } catch (err: any) {
    if (isLocalhost && (err?.code === "ECONNREFUSED" || err?.cause?.code === "ECONNREFUSED")) {
      console.error("\n❌ Could not connect to local PostgreSQL (127.0.0.1:5432).");
      console.error(
        "👉 If you are using Neon, please replace DATABASE_URL in `.env.local` with your Neon connection string:\n" +
          '   DATABASE_URL="postgresql://<user>:<password>@ep-xxx-pooler.region.aws.neon.tech/neondb?sslmode=require"\n' +
          "   Save the file, then re-run `npx tsx scripts/migrate.ts`.\n"
      );
    }
    throw err;
  } finally {
    await pool.end();
  }
}

main().catch((err) => {
  console.error("Migration failed:", err.message ?? err);
  process.exit(1);
});

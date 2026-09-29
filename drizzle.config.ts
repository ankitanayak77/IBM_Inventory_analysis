import { defineConfig } from "drizzle-kit";

/**
 * Uses generate + migrate (versioned SQL migration files under
 * drizzle/migrations/), not `drizzle-kit push` — push is fine for rapid
 * local prototyping but doesn't produce an auditable, repeatable migration
 * history, which this project needs since it's meant to reach a real
 * production database (Neon), not stay a local-only prototype.
 */
export default defineConfig({
  dialect: "postgresql",
  schema: "./src/db/schema.ts",
  out: "./drizzle/migrations",
  dbCredentials: {
    url: process.env.DATABASE_URL!,
  },
});

import { config } from "dotenv";
config({ path: ".env.local" });

import { createUser, listUsers } from "../src/db/userRepository";

/**
 * Provisions a user account. Run with:
 *   npx tsx scripts/create-user.ts owner@example.com "a-strong-password" "Owner Name" owner_manager
 *   npx tsx scripts/create-user.ts staff@example.com "another-password" "Staff Name" staff
 *
 * No public signup route exists on purpose — see userRepository.ts's
 * comment on why. This script is how an admin (you) provisions accounts.
 */
async function main() {
  const [email, password, name, role] = process.argv.slice(2);

  if (!email || !password || !name || !role) {
    console.error("Usage: npx tsx scripts/create-user.ts <email> <password> <name> <owner_manager|staff>");
    process.exit(1);
  }
  if (role !== "owner_manager" && role !== "staff") {
    console.error(`Invalid role "${role}" — must be "owner_manager" or "staff".`);
    process.exit(1);
  }
  if (password.length < 8) {
    console.error("Password must be at least 8 characters.");
    process.exit(1);
  }

  const user = await createUser({ email, password, name, role });
  console.log("Created user:", { id: user.id, email: user.email, name: user.name, role: user.role });

  const all = await listUsers();
  console.log(`\nAll users (${all.length}):`);
  for (const u of all) console.log(`  #${u.id}  ${u.email}  (${u.role})  — ${u.name}`);

  process.exit(0);
}

main().catch((err: any) => {
  const isConnRefused =
    err?.code === "ECONNREFUSED" ||
    err?.cause?.code === "ECONNREFUSED" ||
    (typeof err?.message === "string" && err.message.includes("ECONNREFUSED"));

  if (isConnRefused) {
    console.error("\n❌ Database connection refused.");
    console.error(
      "👉 Please check `.env.local`:\n" +
        "   1. Ensure `DATABASE_URL` is set to your Neon connection string (not 127.0.0.1:5432).\n" +
        "   2. Make sure you have run migrations: `npx tsx scripts/migrate.ts`.\n"
    );
  } else {
    console.error("Failed to create user:", err.message ?? err);
  }
  process.exit(1);
});

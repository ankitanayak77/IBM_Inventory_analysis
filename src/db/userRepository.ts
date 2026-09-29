import { eq } from "drizzle-orm";
import { getDb } from "./client";
import { users } from "./schema";
import { hashPassword } from "@/lib/auth/password";

export type UserRole = "owner_manager" | "staff";

export interface AppUser {
  id: number;
  email: string;
  name: string;
  role: UserRole;
}

/** Looks up a user by email, including the password hash — for the Credentials provider's authorize() only. */
export async function findUserByEmailWithHash(email: string) {
  const db = getDb();
  const [row] = await db.select().from(users).where(eq(users.email, email.toLowerCase()));
  if (!row) return null;
  return {
    id: row.id,
    email: row.email,
    name: row.name,
    role: row.role as UserRole,
    passwordHash: row.passwordHash,
  };
}

/**
 * Creates a user account. Deliberately not exposed as a public self-signup
 * API route: for a small-business inventory tool, the owner provisions
 * staff accounts (see scripts/create-user.ts), not the public — an open
 * signup endpoint that could mint "owner_manager" accounts would be a real
 * security hole, not a convenience feature.
 */
export async function createUser(input: { email: string; password: string; name: string; role: UserRole }): Promise<AppUser> {
  const db = getDb();
  const passwordHash = await hashPassword(input.password);
  const [row] = await db
    .insert(users)
    .values({ email: input.email.toLowerCase(), passwordHash, name: input.name, role: input.role })
    .returning({ id: users.id, email: users.email, name: users.name, role: users.role });
  return { id: row.id, email: row.email, name: row.name, role: row.role as UserRole };
}

export async function listUsers(): Promise<AppUser[]> {
  const db = getDb();
  const rows = await db.select({ id: users.id, email: users.email, name: users.name, role: users.role }).from(users);
  return rows.map((r) => ({ ...r, role: r.role as UserRole }));
}

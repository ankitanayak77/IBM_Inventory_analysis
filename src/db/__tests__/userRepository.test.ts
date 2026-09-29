import { describe, it, expect, beforeAll, afterEach } from "vitest";
import { sql } from "drizzle-orm";
import { getDb, _resetPoolForTests } from "../client";
import { users } from "../schema";
import { createUser, findUserByEmailWithHash, listUsers } from "../userRepository";
import { verifyPassword } from "@/lib/auth/password";
import { checkDbAvailable } from "../dbAvailable";

const DB_AVAILABLE = await checkDbAvailable();

describe.skipIf(!DB_AVAILABLE)("userRepository — against a real Postgres database", () => {
  beforeAll(() => {
    _resetPoolForTests();
  });

  afterEach(async () => {
    await getDb().execute(sql`TRUNCATE TABLE ${users} RESTART IDENTITY CASCADE`);
  });

  it("creates a user with a hashed password, never returning the hash itself", async () => {
    const user = await createUser({
      email: "Owner@Example.com", // mixed case — confirm normalization
      password: "correct-horse-battery-staple",
      name: "Test Owner",
      role: "owner_manager",
    });

    expect(user.email).toBe("owner@example.com"); // normalized to lowercase
    expect(user.role).toBe("owner_manager");
    expect((user as unknown as { passwordHash?: string }).passwordHash).toBeUndefined();
  });

  it("looks up a user by email (case-insensitive) with the password hash for authorize()", async () => {
    await createUser({ email: "staff@example.com", password: "a-staff-password", name: "Staff Person", role: "staff" });

    const found = await findUserByEmailWithHash("STAFF@example.com");
    expect(found).not.toBeNull();
    expect(found!.role).toBe("staff");
    expect(await verifyPassword(found!.passwordHash, "a-staff-password")).toBe(true);
    expect(await verifyPassword(found!.passwordHash, "wrong-password")).toBe(false);
  });

  it("returns null for an email that doesn't exist", async () => {
    const found = await findUserByEmailWithHash("nobody@example.com");
    expect(found).toBeNull();
  });

  it("enforces unique emails at the database level", async () => {
    await createUser({ email: "dup@example.com", password: "password-one", name: "First", role: "staff" });
    await expect(
      createUser({ email: "dup@example.com", password: "password-two", name: "Second", role: "owner_manager" })
    ).rejects.toThrow();
  });

  it("lists users without their password hashes", async () => {
    await createUser({ email: "a@example.com", password: "password-a-123", name: "A", role: "owner_manager" });
    await createUser({ email: "b@example.com", password: "password-b-123", name: "B", role: "staff" });

    const all = await listUsers();
    expect(all.length).toBe(2);
    for (const u of all) {
      expect((u as unknown as { passwordHash?: string }).passwordHash).toBeUndefined();
    }
  });
});

import { describe, it, expect, beforeAll, afterAll, beforeEach } from "vitest";
import { sql } from "drizzle-orm";
import { getDb, _resetPoolForTests } from "@/db/client";
import { users, loginAttempts } from "@/db/schema";
import { createUser } from "@/db/userRepository";
import { authOptions } from "../authOptions";
import { checkDbAvailable } from "@/db/dbAvailable";

const DB_AVAILABLE = await checkDbAvailable();

/**
 * Tests the real Credentials provider's authorize() callback end-to-end
 * against the actual database — not a mock of the DB layer. Accessed via
 * `authOptions.providers[0].options.authorize`, not
 * `authOptions.providers[0].authorize` directly: confirmed by reading
 * next-auth's own source (providers/credentials.ts) that the factory
 * function returns a hardcoded `authorize: () => null` stub at the top
 * level, with the real, user-supplied authorize function stashed under a
 * nested `options` property instead — NextAuth's internal request
 * handling merges the two before a real login, but calling the top-level
 * field directly (as an early version of this test did) silently invokes
 * the stub and always returns null. Caught by checking `provider.authorize
 * === provider.options.authorize` (false) before trusting either result.
 */
describe.skipIf(!DB_AVAILABLE)("authOptions Credentials provider — authorize() against a real database", () => {
  beforeAll(async () => {
    _resetPoolForTests();
    await getDb().execute(sql`TRUNCATE TABLE ${users} RESTART IDENTITY CASCADE`);
    await createUser({ email: "owner@example.com", password: "correct-owner-password", name: "Test Owner", role: "owner_manager" });
    await createUser({ email: "staff@example.com", password: "correct-staff-password", name: "Test Staff", role: "staff" });
  });

  // Every test in this file now calls the real authorize(), which records
  // a login_attempts row on every call (success or failure) — added by
  // the rate-limiting hardening pass. Without this, an earlier test's
  // wrong-password attempt would silently count toward a *later* test's
  // rate-limit threshold, since this table isn't otherwise touched
  // between tests — exactly the kind of cross-test leakage this project
  // has caught and fixed before (see the DATABASE_URL-scoping comments
  // elsewhere in this codebase for the same category of issue).
  beforeEach(async () => {
    await getDb().execute(sql`TRUNCATE TABLE ${loginAttempts} RESTART IDENTITY`);
  });

  afterAll(async () => {
    await getDb().execute(sql`TRUNCATE TABLE ${users} RESTART IDENTITY CASCADE`);
    await getDb().execute(sql`TRUNCATE TABLE ${loginAttempts} RESTART IDENTITY`);
  });

  function authorize(credentials: Record<string, string> | undefined) {
    const provider = authOptions.providers[0] as unknown as {
      authorize: unknown;
      options: {
        authorize: (c: typeof credentials, req: object) => Promise<{ id: string; email: string; name: string; role: string } | null>;
      };
    };
    // Sanity-check every run that we are calling the real function, not
    // the top-level stub — regression guard for the exact mistake above.
    expect(provider.authorize).not.toBe(provider.options.authorize);
    return provider.options.authorize(credentials, {});
  }

  it("returns the user (with role) for correct owner_manager credentials", async () => {
    const user = await authorize({ email: "owner@example.com", password: "correct-owner-password" });
    expect(user).toEqual({ id: "1", email: "owner@example.com", name: "Test Owner", role: "owner_manager" });
  });

  it("returns the user (with role) for correct staff credentials", async () => {
    const user = await authorize({ email: "staff@example.com", password: "correct-staff-password" });
    expect(user).toMatchObject({ email: "staff@example.com", role: "staff" });
  });

  it("returns null for a wrong password", async () => {
    expect(await authorize({ email: "owner@example.com", password: "wrong-password" })).toBeNull();
  });

  it("returns null for an email that doesn't exist", async () => {
    expect(await authorize({ email: "nobody@example.com", password: "anything" })).toBeNull();
  });

  it("is case-insensitive on email", async () => {
    const user = await authorize({ email: "OWNER@EXAMPLE.COM", password: "correct-owner-password" });
    expect(user?.email).toBe("owner@example.com");
  });

  it("returns null when the password field is missing", async () => {
    expect(await authorize({ email: "owner@example.com" })).toBeNull();
  });

  it("returns null when credentials are undefined entirely", async () => {
    expect(await authorize(undefined)).toBeNull();
  });

  it("REGRESSION/hardening: after enough failed attempts, even the correct password is rejected (rate limited)", async () => {
    const { RATE_LIMIT_MAX_FAILURES } = await import("@/db/loginAttemptRepository");
    for (let i = 0; i < RATE_LIMIT_MAX_FAILURES; i++) {
      const result = await authorize({ email: "owner@example.com", password: "wrong-password" });
      expect(result).toBeNull();
    }
    // Now at the threshold — even the genuinely correct password must be rejected.
    const result = await authorize({ email: "owner@example.com", password: "correct-owner-password" });
    expect(result).toBeNull();
  });

  it("a rate-limited attempt does not itself count as a new failure (no perpetually-extending lockout)", async () => {
    const { countRecentFailedAttempts, RATE_LIMIT_MAX_FAILURES } = await import("@/db/loginAttemptRepository");
    for (let i = 0; i < RATE_LIMIT_MAX_FAILURES; i++) {
      await authorize({ email: "owner@example.com", password: "wrong-password" });
    }
    const countAtThreshold = await countRecentFailedAttempts("owner@example.com");
    expect(countAtThreshold).toBe(RATE_LIMIT_MAX_FAILURES);

    // Two more attempts while already rate-limited — the count must not grow.
    await authorize({ email: "owner@example.com", password: "wrong-password" });
    await authorize({ email: "owner@example.com", password: "correct-owner-password" });
    expect(await countRecentFailedAttempts("owner@example.com")).toBe(RATE_LIMIT_MAX_FAILURES);
  });

  it("rate limiting is per-email: a different account is unaffected by another account's lockout", async () => {
    const { RATE_LIMIT_MAX_FAILURES } = await import("@/db/loginAttemptRepository");
    for (let i = 0; i < RATE_LIMIT_MAX_FAILURES; i++) {
      await authorize({ email: "owner@example.com", password: "wrong-password" });
    }
    // owner@example.com is now locked out; staff@example.com must still work normally.
    const staffResult = await authorize({ email: "staff@example.com", password: "correct-staff-password" });
    expect(staffResult).toMatchObject({ email: "staff@example.com", role: "staff" });
  });

  it("staying under the threshold does not block a subsequent correct login", async () => {
    const { RATE_LIMIT_MAX_FAILURES } = await import("@/db/loginAttemptRepository");
    for (let i = 0; i < RATE_LIMIT_MAX_FAILURES - 1; i++) {
      await authorize({ email: "owner@example.com", password: "wrong-password" });
    }
    const result = await authorize({ email: "owner@example.com", password: "correct-owner-password" });
    expect(result).toMatchObject({ email: "owner@example.com", role: "owner_manager" });
  });
});

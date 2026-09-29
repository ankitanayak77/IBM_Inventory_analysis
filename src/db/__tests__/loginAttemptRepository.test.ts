import { describe, it, expect, beforeAll, afterAll, beforeEach } from "vitest";
import { sql } from "drizzle-orm";
import { getDb, _resetPoolForTests } from "../client";
import { loginAttempts } from "../schema";
import { recordLoginAttempt, countRecentFailedAttempts, isRateLimited, RATE_LIMIT_MAX_FAILURES } from "../loginAttemptRepository";
import { checkDbAvailable } from "../dbAvailable";

const DB_AVAILABLE = await checkDbAvailable();

describe.skipIf(!DB_AVAILABLE)("loginAttemptRepository — against a real Postgres database", () => {
  beforeAll(() => {
    _resetPoolForTests();
  });

  beforeEach(async () => {
    await getDb().execute(sql`TRUNCATE TABLE ${loginAttempts} RESTART IDENTITY`);
  });

  afterAll(async () => {
    await getDb().execute(sql`TRUNCATE TABLE ${loginAttempts} RESTART IDENTITY`);
  });

  it("countRecentFailedAttempts returns 0 for an email with no attempts at all", async () => {
    expect(await countRecentFailedAttempts("nobody@example.com")).toBe(0);
  });

  it("counts only failed attempts, not successful ones", async () => {
    await recordLoginAttempt("test@example.com", false);
    await recordLoginAttempt("test@example.com", false);
    await recordLoginAttempt("test@example.com", true); // a success mixed in
    expect(await countRecentFailedAttempts("test@example.com")).toBe(2);
  });

  it("is case-insensitive on email, matching userRepository's own normalization", async () => {
    await recordLoginAttempt("Test@Example.com", false);
    expect(await countRecentFailedAttempts("test@example.com")).toBe(1);
    expect(await countRecentFailedAttempts("TEST@EXAMPLE.COM")).toBe(1);
  });

  it("does not count another email's failed attempts", async () => {
    await recordLoginAttempt("a@example.com", false);
    await recordLoginAttempt("a@example.com", false);
    await recordLoginAttempt("b@example.com", false);
    expect(await countRecentFailedAttempts("a@example.com")).toBe(2);
    expect(await countRecentFailedAttempts("b@example.com")).toBe(1);
  });

  it("isRateLimited is false below the threshold and true at or above it", async () => {
    for (let i = 0; i < RATE_LIMIT_MAX_FAILURES - 1; i++) {
      await recordLoginAttempt("threshold@example.com", false);
    }
    expect(await isRateLimited("threshold@example.com")).toBe(false); // one short of the limit

    await recordLoginAttempt("threshold@example.com", false); // now exactly at the limit
    expect(await isRateLimited("threshold@example.com")).toBe(true);
  });

  it("does not count attempts outside the rate-limit window", async () => {
    const db = getDb();
    // Insert an old failed attempt directly, bypassing recordLoginAttempt
    // (which always uses "now"), to simulate one from outside the window.
    await db.insert(loginAttempts).values({
      email: "old@example.com",
      succeeded: false,
      attemptedAt: new Date(Date.now() - 60 * 60 * 1000), // 1 hour ago — outside the 15-minute window
    });
    expect(await countRecentFailedAttempts("old@example.com")).toBe(0);
  });
});

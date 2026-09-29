import { and, eq, gte, sql } from "drizzle-orm";
import { getDb } from "./client";
import { loginAttempts } from "./schema";

/**
 * Threshold matches common practice across mainstream auth
 * implementations (e.g. Django-axes' and most managed-auth providers'
 * defaults cluster around 5 failures / 15 minutes) — a reasonable,
 * configurable default, not a number invented for this app specifically.
 */
export const RATE_LIMIT_MAX_FAILURES = 5;
export const RATE_LIMIT_WINDOW_MINUTES = 15;

export async function recordLoginAttempt(email: string, succeeded: boolean): Promise<void> {
  const db = getDb();
  await db.insert(loginAttempts).values({ email: email.toLowerCase(), succeeded });
}

/** Counts failed login attempts for this email within the rate-limit window. */
export async function countRecentFailedAttempts(email: string): Promise<number> {
  const db = getDb();
  const windowStart = new Date(Date.now() - RATE_LIMIT_WINDOW_MINUTES * 60 * 1000);

  const [row] = await db
    .select({ count: sql<number>`count(*)::int` })
    .from(loginAttempts)
    .where(
      and(
        eq(loginAttempts.email, email.toLowerCase()),
        eq(loginAttempts.succeeded, false),
        gte(loginAttempts.attemptedAt, windowStart)
      )
    );

  return row?.count ?? 0;
}

/**
 * Checked BEFORE password verification in authorize() — not just before
 * returning a result. This matters for a reason beyond just blocking
 * excess attempts: Argon2id is deliberately memory-hard (64 MiB per
 * verification — see password.ts), so letting an already-rate-limited
 * flood of requests each still pay that memory cost before being
 * rejected would itself be a resource-exhaustion vector this check
 * exists partly to close.
 */
export async function isRateLimited(email: string): Promise<boolean> {
  const failures = await countRecentFailedAttempts(email);
  return failures >= RATE_LIMIT_MAX_FAILURES;
}

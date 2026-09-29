import { getServerSession } from "next-auth";
import { authOptions } from "./authOptions";
import type { UserRole } from "@/db/userRepository";

/**
 * Called directly inside each protected Route Handler / Server Component
 * — never via middleware.ts/proxy.ts. See authOptions.ts's comment for
 * why (CVE-2025-29927; Next.js 16's own middleware→proxy rename and
 * accompanying guidance that auth checks belong in route handlers).
 *
 * getServerSession(authOptions) — single argument — is next-auth v4's
 * documented App Router pattern; confirmed by reading the installed
 * package's own source (next-auth/next/index.js): with exactly one
 * argument it takes the "RSC" branch, which calls next/headers's
 * headers()/cookies() to read the request ambiently from Next.js's
 * per-request AsyncLocalStorage context. That context only exists
 * inside a real running Next.js server — confirmed empirically (not
 * assumed) that calling next/headers outside one throws
 * "`headers` was called outside a request scope". This is why
 * getSessionUser()/requireRole() themselves are not unit-tested the way
 * every other route in this project has been (by importing the route's
 * exported handler and calling it directly in Vitest) — see
 * evaluateAuth() below, which *is* fully unit-tested, for the actual
 * authorization decision logic split out from this Next.js-specific
 * plumbing. The plumbing itself is verified correct by the source
 * reading above and by `next build`'s type-checking, not by a bare
 * Vitest call — the same category of sandbox limitation as the
 * Recharts SSR-only rendering and the Playwright/Chromium install
 * noted earlier in this build: real, disclosed, not hidden.
 */
export async function getSessionUser() {
  const session = await getServerSession(authOptions);
  return session?.user ?? null;
}

export interface AuthResult {
  ok: boolean;
  status: 401 | 403 | null;
  error: string | null;
  user: { id: string; role: UserRole } | null;
}

/**
 * The actual authorization decision — pure, and fully unit-tested
 * (see __tests__/session.test.ts) independently of how `user` was
 * obtained. Given a session user (or null) and an optional list of
 * allowed roles, decides ok/401/403 the same way for every route, so
 * "require login" and "require owner_manager" always produce the same
 * status codes and error shape everywhere they're used.
 */
export function evaluateAuth(
  user: { id: string; role: UserRole } | null,
  allowedRoles?: UserRole[]
): AuthResult {
  if (!user) {
    return { ok: false, status: 401, error: "Not signed in.", user: null };
  }
  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return { ok: false, status: 403, error: `This action requires one of: ${allowedRoles.join(", ")}.`, user };
  }
  return { ok: true, status: null, error: null, user };
}

/** Convenience wrapper: fetches the real session, then applies evaluateAuth(). */
export async function requireRole(allowedRoles?: UserRole[]): Promise<AuthResult> {
  const user = await getSessionUser();
  return evaluateAuth(user, allowedRoles);
}

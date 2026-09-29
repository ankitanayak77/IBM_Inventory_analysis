import type { NextAuthOptions } from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";
import { findUserByEmailWithHash } from "@/db/userRepository";
import { verifyPassword } from "./password";
import { isRateLimited, recordLoginAttempt } from "@/db/loginAttemptRepository";

/**
 * Report FR-9 ("Support role-based views"). Credentials provider + JWT
 * sessions, no database adapter — see schema.ts's comment on `users` for
 * why (NextAuth's own FAQ: user accounts are never persisted via an
 * adapter when a custom Credentials provider is used; JWT sessions are
 * required). `next-auth@4.24.15` specifically — the real current stable
 * release confirmed against the npm registry directly, not the 5.x line,
 * which is still only published under the `beta` dist-tag after 2+ years
 * (verified, not assumed from blog posts claiming otherwise — see
 * conversation).
 *
 * No signup route: accounts are provisioned via scripts/create-user.ts,
 * not a public endpoint — see userRepository.ts's comment on why an open
 * signup would be a real security hole for this kind of app, not a
 * convenience.
 *
 * Deliberately no middleware.ts/proxy.ts for route protection. Two
 * independent, current reasons found during research: (1) CVE-2025-29927
 * demonstrated middleware-only session checks are bypassable by spoofing
 * the x-middleware-subrequest header; (2) Next.js 16 itself renamed
 * middleware.ts to proxy.ts specifically to make clear that this file is
 * for network-level operations, not security — official guidance is that
 * auth checks belong directly in route handlers/layouts. Every protected
 * route in this app (see api/upload, api/export/pdf, api/datasets) calls
 * getServerSession(authOptions) itself.
 */
export const authOptions: NextAuthOptions = {
  session: { strategy: "jwt" },
  pages: { signIn: "/login" },
  providers: [
    CredentialsProvider({
      name: "Credentials",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) return null;
        const email = credentials.email;

        // Hardening (Report Chapter 15, Phase 5): checked BEFORE the
        // database lookup or password verification, not after — a
        // rate-limited email is rejected without ever reaching
        // verifyPassword's Argon2id call (64 MiB/attempt, deliberately
        // memory-hard — see password.ts), which is itself part of the
        // point: letting an attack's requests each still pay that memory
        // cost before being rejected would be a resource-exhaustion
        // vector this check exists partly to close. Deliberately does
        // NOT record this blocked attempt as another failure — that
        // would let an attacker perpetually extend their own lockout
        // window by continuing to hammer the endpoint after already
        // being blocked, which only hurts the legitimate account owner.
        if (await isRateLimited(email)) {
          return null;
        }

        const user = await findUserByEmailWithHash(email);
        if (!user) {
          await recordLoginAttempt(email, false);
          return null;
        }

        const valid = await verifyPassword(user.passwordHash, credentials.password);
        await recordLoginAttempt(email, valid);
        if (!valid) return null;

        return { id: String(user.id), email: user.email, name: user.name, role: user.role };
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.id = user.id;
        token.role = user.role;
      }
      return token;
    },
    async session({ session, token }) {
      session.user.id = token.id;
      session.user.role = token.role;
      return session;
    },
  },
  secret: process.env.NEXTAUTH_SECRET,
};

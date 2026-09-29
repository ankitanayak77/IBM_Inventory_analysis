import type { DefaultSession } from "next-auth";
import type { UserRole } from "@/db/userRepository";

/**
 * Module augmentation so `session.user.role` / `session.user.id` and the
 * JWT's `role`/`id` fields are properly typed everywhere, instead of
 * `as any`-casting at every call site (the JWT/session callbacks in
 * authOptions.ts, and every protected route handler that reads them).
 */
declare module "next-auth" {
  interface Session {
    user: {
      id: string;
      role: UserRole;
    } & DefaultSession["user"];
  }

  interface User {
    id: string;
    role: UserRole;
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    id: string;
    role: UserRole;
  }
}

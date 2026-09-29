import NextAuth from "next-auth";
import { authOptions } from "@/lib/auth/authOptions";

// The documented next-auth v4 App Router pattern (confirmed against the
// project's own historical docs commit during research, not assumed) —
// a single catch-all route handler exporting the same handler as both
// GET and POST.
const handler = NextAuth(authOptions);
export { handler as GET, handler as POST };

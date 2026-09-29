import type { NextConfig } from "next";

/**
 * Hardening (Report Chapter 15, Phase 5). Headers chosen from Next.js's
 * own documented security-headers list — kept to the ones with no
 * realistic chance of breaking this specific app (no CSP here: getting
 * a Content-Security-Policy right without breaking Tailwind's
 * runtime-injected styles or Recharts' inline SVG would need a real
 * browser to verify against, which this sandbox doesn't have — noted as
 * a follow-up in BUILD_NOTES.md rather than shipped unverified).
 */
const securityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" }, // stop the browser guessing a response's MIME type
  { key: "X-Frame-Options", value: "DENY" }, // this app has no reason to be framed by anyone
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" }, // none of this app's features need any of these
];

const nextConfig: NextConfig = {
  // Pins Turbopack's workspace-root inference to this project's own
  // directory explicitly — confirmed against real first-party evidence,
  // not assumed: a user running this app reported Turbopack getting
  // confused by *other*, unrelated package-lock.json files sitting in
  // parent directories of wherever this project was extracted to (their
  // home folder and Downloads both had their own lockfiles), which made
  // Turbopack infer the wrong workspace root and warn about it. `root`
  // (confirmed as the real, current option name and type — `root?:
  // string` — directly from node_modules/next's own installed type
  // definitions, not guessed from the warning text alone) removes that
  // ambiguity regardless of where this project sits relative to other,
  // unrelated Node projects on someone's machine.
  turbopack: {
    root: __dirname,
  },
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
};

export default nextConfig;

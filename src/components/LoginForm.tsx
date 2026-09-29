"use client";

import { useState, type FormEvent } from "react";
import { signIn } from "next-auth/react";
import { useSearchParams } from "next/navigation";

/**
 * Report FR-9. `signIn("credentials", ...)` doesn't require a
 * <SessionProvider> ancestor (confirmed by reading next-auth's own
 * react.js source — it's a standalone fetch-based function); this app
 * checks sessions server-side (getServerSession in Server Components /
 * Route Handlers) rather than via the client useSession() hook, which is
 * the one thing that does need SessionProvider — not used here.
 */
export function LoginForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const [error, setError] = useState<string | null>(null);
  const searchParams = useSearchParams();
  const callbackUrl = searchParams.get("callbackUrl") || "/";

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setStatus("loading");
    setError(null);

    const result = await signIn("credentials", { email, password, redirect: false, callbackUrl });

    if (result?.error) {
      setStatus("error");
      setError("Incorrect email or password.");
      return;
    }
    window.location.href = result?.url ?? callbackUrl;
  }

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
      <div className="w-full max-w-sm bg-white rounded-lg border border-slate-200 shadow-sm p-6">
        <h1 className="text-xl font-bold text-[var(--color-navy)] mb-1">Inventory Analysis</h1>
        <p className="text-sm text-slate-500 mb-6">Sign in to view your dashboard.</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1" htmlFor="email">
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              autoComplete="email"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1" htmlFor="password">
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              autoComplete="current-password"
            />
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <button
            type="submit"
            disabled={status === "loading"}
            className="w-full bg-[var(--color-navy)] text-white text-sm font-medium py-2 rounded-md disabled:opacity-50"
          >
            {status === "loading" ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <p className="text-xs text-slate-400 mt-4">
          No account? Ask an owner/manager to provision one — see <code>scripts/create-user.ts</code>.
        </p>
      </div>
    </div>
  );
}

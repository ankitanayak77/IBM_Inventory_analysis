"use client";

import { signOut } from "next-auth/react";

export function SignOutButton() {
  return (
    <button
      onClick={() => signOut({ callbackUrl: "/login" })}
      className="text-sm text-slate-300 hover:text-white underline underline-offset-2"
    >
      Sign out
    </button>
  );
}

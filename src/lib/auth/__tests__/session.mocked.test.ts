import { describe, it, expect, vi } from "vitest";

// Mocking getServerSession itself, not next/headers — this is the
// standard, documented way to test next-auth-protected code without a
// real running Next.js server: next/headers's ambient request-scope
// requirement (confirmed to throw outside one — see session.ts's
// comment) is entirely next-auth's internal concern once
// getServerSession is mocked at the module boundary.
vi.mock("next-auth", () => ({
  getServerSession: vi.fn(),
}));

import { getServerSession } from "next-auth";
import { getSessionUser, requireRole } from "../session";

describe("getSessionUser / requireRole with a mocked getServerSession", () => {
  it("returns null when there is no session", async () => {
    vi.mocked(getServerSession).mockResolvedValueOnce(null);
    const user = await getSessionUser();
    expect(user).toBeNull();
  });

  it("returns the session user when a session exists", async () => {
    vi.mocked(getServerSession).mockResolvedValueOnce({
      user: { id: "5", role: "owner_manager" },
    } as never);
    const user = await getSessionUser();
    expect(user).toEqual({ id: "5", role: "owner_manager" });
  });

  it("requireRole combines the mocked session with evaluateAuth correctly (401 case)", async () => {
    vi.mocked(getServerSession).mockResolvedValueOnce(null);
    const result = await requireRole(["owner_manager"]);
    expect(result.status).toBe(401);
  });

  it("requireRole combines the mocked session with evaluateAuth correctly (403 case)", async () => {
    vi.mocked(getServerSession).mockResolvedValueOnce({ user: { id: "1", role: "staff" } } as never);
    const result = await requireRole(["owner_manager"]);
    expect(result.status).toBe(403);
  });

  it("requireRole combines the mocked session with evaluateAuth correctly (200/ok case)", async () => {
    vi.mocked(getServerSession).mockResolvedValueOnce({ user: { id: "1", role: "owner_manager" } } as never);
    const result = await requireRole(["owner_manager"]);
    expect(result.ok).toBe(true);
  });
});

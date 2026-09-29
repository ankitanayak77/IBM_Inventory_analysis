import { describe, it, expect } from "vitest";
import { evaluateAuth } from "../session";

describe("evaluateAuth — the authorization decision logic (pure, no Next.js context needed)", () => {
  it("returns 401 when there is no user at all", () => {
    const result = evaluateAuth(null);
    expect(result.ok).toBe(false);
    expect(result.status).toBe(401);
    expect(result.error).toMatch(/not signed in/i);
  });

  it("returns 401 for an unauthenticated request even when specific roles are required", () => {
    const result = evaluateAuth(null, ["owner_manager"]);
    expect(result.status).toBe(401); // 401, not 403 — no identity to check a role against
  });

  it("allows any authenticated user when no roles are specified", () => {
    const result = evaluateAuth({ id: "1", role: "staff" });
    expect(result.ok).toBe(true);
    expect(result.status).toBeNull();
    expect(result.user?.role).toBe("staff");
  });

  it("returns 403 when the user's role is not in the allowed list", () => {
    const result = evaluateAuth({ id: "1", role: "staff" }, ["owner_manager"]);
    expect(result.ok).toBe(false);
    expect(result.status).toBe(403);
    expect(result.error).toMatch(/owner_manager/);
    expect(result.user?.role).toBe("staff"); // identity is still known, just not permitted
  });

  it("allows the request when the user's role is in the allowed list", () => {
    const result = evaluateAuth({ id: "2", role: "owner_manager" }, ["owner_manager"]);
    expect(result.ok).toBe(true);
    expect(result.status).toBeNull();
  });

  it("allows the request when the allowed list has multiple roles and the user matches one", () => {
    const result = evaluateAuth({ id: "3", role: "staff" }, ["owner_manager", "staff"]);
    expect(result.ok).toBe(true);
  });
});

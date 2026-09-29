import { describe, it, expect, vi } from "vitest";

vi.mock("next-auth", () => ({ getServerSession: vi.fn() }));
import { getServerSession } from "next-auth";
import { GET } from "../route";

function mockSession(role: "owner_manager" | "staff" | null) {
  vi.mocked(getServerSession).mockResolvedValue(role ? ({ user: { id: "1", role } } as never) : null);
}

describe("GET /api/analysis/recommendations", () => {
  it("returns 401 when there is no session", async () => {
    mockSession(null);
    const req = new Request("http://localhost:3000/api/analysis/recommendations");
    const response = await GET(req);
    expect(response.status).toBe(401);
  });

  it("returns full recommendations and executive metrics for an owner_manager", async () => {
    mockSession("owner_manager");
    const req = new Request("http://localhost:3000/api/analysis/recommendations");
    const response = await GET(req);
    expect(response.status).toBe(200);
    const body = await response.json();

    expect(body.role).toBe("owner_manager");
    expect(body.sourceLabel).toBe("sample dataset");
    expect(body.healthScore).toBeGreaterThan(50);
    expect(body.healthGrade).toBeDefined();
    expect(body.totalReplenishmentCost).toBeGreaterThan(0);
    expect(body.trappedCapitalInDeadStock).toBeGreaterThanOrEqual(0);
    expect(body.items.length).toBeGreaterThan(0);
    expect(body.supplierRiskSummary.length).toBeGreaterThan(0);
    expect(body.executiveSummaryText).toContain("Portfolio Health Score");
  });

  it("returns replenishment-only action list for a staff session", async () => {
    mockSession("staff");
    const req = new Request("http://localhost:3000/api/analysis/recommendations");
    const response = await GET(req);
    expect(response.status).toBe(200);
    const body = await response.json();

    expect(body.role).toBe("staff");
    expect(body.sourceLabel).toBe("sample dataset");
    expect(body.items.length).toBeGreaterThan(0);
    // Every item returned to staff must be a replenishment item
    for (const item of body.items) {
      expect(item.type).toBe("replenishment");
    }
    // High-level financial KPIs must be hidden from staff
    expect(body.healthScore).toBeUndefined();
    expect(body.trappedCapitalInDeadStock).toBeUndefined();
    expect(body.trappedCapitalInSlowMoving).toBeUndefined();
    expect(body.supplierRiskSummary).toBeUndefined();
  });
});

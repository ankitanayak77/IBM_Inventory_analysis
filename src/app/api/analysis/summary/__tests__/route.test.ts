import { describe, it, expect, vi } from "vitest";

// See src/app/api/upload/__tests__/route.test.ts's comment for why this
// mocking approach (not next/headers) is the correct way to test a
// next-auth-protected route outside a real running Next.js server.
vi.mock("next-auth", () => ({ getServerSession: vi.fn() }));
import { getServerSession } from "next-auth";
import { GET } from "../route";

function mockSession(role: "owner_manager" | "staff" | null) {
  vi.mocked(getServerSession).mockResolvedValue(role ? ({ user: { id: "1", role } } as never) : null);
}

describe("GET /api/analysis/summary", () => {
  it("returns 401 when there is no session", async () => {
    mockSession(null);
    const response = await GET();
    expect(response.status).toBe(401);
  });

  it("returns the full AnalysisResult, matching the report's numbers, for an owner_manager", async () => {
    mockSession("owner_manager");
    const response = await GET();
    expect(response.status).toBe(200);
    const body = await response.json();

    expect(body.skuCount).toBe(50);
    expect(body.kpis.totalInventoryValue).toBeCloseTo(21913.5, 1);
    const fsnCounts: Record<string, number> = {};
    for (const row of body.fsn) fsnCounts[row.fsn_class] = row.skuCount;
    expect(fsnCounts["Fast-moving"]).toBe(10);
    expect(body.reorderRisk.length).toBe(7);
  });

  it("returns only the restricted staff view (Report FR-9) for a staff session", async () => {
    mockSession("staff");
    const response = await GET();
    expect(response.status).toBe(200);
    const body = await response.json();

    expect(body.role).toBe("staff");
    expect(body.sourceLabel).toBe("sample dataset");
    expect(body.reorderRisk.length).toBe(7); // same 7 SKUs the report verifies (Section 4.5)
    expect(body.kpis).toBeUndefined();
    expect(body.fsn).toBeUndefined();
    expect(body.abc).toBeUndefined();
    expect(body.rows).toBeUndefined();
    expect(body.pareto).toBeUndefined();
    expect(body.categoryPerf).toBeUndefined();
    expect(body.matrix).toBeUndefined();
  });
});

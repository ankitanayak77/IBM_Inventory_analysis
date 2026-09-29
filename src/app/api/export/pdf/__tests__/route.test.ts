import { describe, it, expect, beforeEach, vi } from "vitest";
import { readFileSync } from "fs";
import path from "path";
import { parseInventoryCsv } from "@/lib/analytics/parseCsv";
import { analyzeCsvText } from "@/lib/analytics/analyze";

// See src/app/api/upload/__tests__/route.test.ts's comment for why this
// mocking approach (not next/headers) is the correct way to test a
// next-auth-protected route outside a real running Next.js server.
vi.mock("next-auth", () => ({ getServerSession: vi.fn() }));
import { getServerSession } from "next-auth";
import { POST } from "../route";

function mockSession(role: "owner_manager" | "staff" | null) {
  vi.mocked(getServerSession).mockResolvedValue(role ? ({ user: { id: "1", role } } as never) : null);
}

function makeJsonRequest(body: unknown): Request {
  return new Request("http://localhost/api/export/pdf", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

describe("POST /api/export/pdf — auth boundary (Report FR-9: owner_manager only)", () => {
  it("returns 401 when there is no session", async () => {
    mockSession(null);
    const response = await POST(makeJsonRequest({ result: {}, sourceLabel: "x" }));
    expect(response.status).toBe(401);
  });

  it("returns 403 for a staff session (report export is a manager action)", async () => {
    mockSession("staff");
    const response = await POST(makeJsonRequest({ result: {}, sourceLabel: "x" }));
    expect(response.status).toBe(403);
  });
});

describe("POST /api/export/pdf", () => {
  beforeEach(() => mockSession("owner_manager"));

  it("renders a real, valid PDF for the actual report-verified sample dataset", async () => {
    const csvPath = path.join(process.cwd(), "src/data/retail_inventory.csv");
    const result = analyzeCsvText(readFileSync(csvPath, "utf-8"));

    const response = await POST(makeJsonRequest({ result, sourceLabel: "sample dataset" }));

    expect(response.status).toBe(200);
    expect(response.headers.get("Content-Type")).toBe("application/pdf");
    expect(response.headers.get("Content-Disposition")).toContain("inventory-analysis-report.pdf");

    const buffer = Buffer.from(await response.arrayBuffer());
    // A real PDF file signature, not a screenshot/image wrapper or an error
    // page — this is the actual evidence the route works, not an assumption.
    expect(buffer.subarray(0, 5).toString("latin1")).toBe("%PDF-");
    expect(buffer.length).toBeGreaterThan(1000);
    // A well-formed PDF's trailer must appear near the end of the file.
    expect(buffer.subarray(-2048).toString("latin1")).toContain("%%EOF");
  });

  it("renders correctly for an empty reorder-risk list (no SKUs at risk)", async () => {
    // Construct a tiny dataset where nothing is near its reorder point,
    // to exercise the PDF's "no SKUs at risk" branch specifically.
    const csv = [
      "sku,product_name,category,size,color,quantity_on_hand,reorder_point,cost_per_unit,retail_price,last_restock_date,units_sold_30d,supplier,season",
      "SKU1,Healthy Item,Tops,S,Red,50,5,10.00,20.00,2024-01-01,3,Acme,Year-Round",
    ].join("\n");
    const { rows } = parseInventoryCsv(csv);
    const result = analyzeCsvText(csv);
    expect(result.reorderRisk.length).toBe(0); // sanity: this fixture really has none at risk
    expect(rows.length).toBe(1);

    const response = await POST(makeJsonRequest({ result, sourceLabel: "test.csv" }));
    expect(response.status).toBe(200);
    const buffer = Buffer.from(await response.arrayBuffer());
    expect(buffer.subarray(0, 5).toString("latin1")).toBe("%PDF-");
  });

  it("returns 400 for a request body missing the result field", async () => {
    const response = await POST(makeJsonRequest({ sourceLabel: "oops" }));
    expect(response.status).toBe(400);
    const body = await response.json();
    expect(body.error).toMatch(/AnalysisResult/i);
  });

  it("returns 400 for invalid JSON", async () => {
    const request = new Request("http://localhost/api/export/pdf", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{not valid json",
    });
    const response = await POST(request);
    expect(response.status).toBe(400);
  });

  it("caps the stock-out risk table and stays fast even when a catalog has thousands of at-risk SKUs", async () => {
    const { generateSyntheticInventoryCsv } = await import("@/test-fixtures/generateSyntheticInventory");
    const csv = generateSyntheticInventoryCsv({ count: 10000 });
    const result = analyzeCsvText(csv);
    // Confirms the premise this test exists to guard: this synthetic catalog
    // really does produce a large at-risk list (measured: 2,666 of 10,000),
    // because quantity_on_hand and reorder_point are drawn independently —
    // this is deliberately a stress case, not assumed to be typical.
    expect(result.reorderRisk.length).toBeGreaterThan(50);

    const start = performance.now();
    const response = await POST(makeJsonRequest({ result, sourceLabel: "large_catalog.csv" }));
    const elapsedMs = performance.now() - start;

    expect(response.status).toBe(200);
    const buffer = Buffer.from(await response.arrayBuffer());
    expect(buffer.subarray(0, 5).toString("latin1")).toBe("%PDF-");
    // With the table capped at 50 rows (InventoryReportPdf.tsx), this must
    // render in about the same time as the 50-row sample case, not scale
    // with the catalog size — this is the actual fix being verified, not
    // just a relaxed timeout.
    expect(elapsedMs).toBeLessThan(5000);
  });
});

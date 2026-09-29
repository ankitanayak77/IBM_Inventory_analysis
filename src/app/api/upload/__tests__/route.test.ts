import { describe, it, expect, beforeAll, afterAll, beforeEach, vi } from "vitest";
import { readFileSync } from "fs";
import path from "path";
import { generateSyntheticInventoryCsv } from "@/test-fixtures/generateSyntheticInventory";

// Mocking getServerSession (not next/headers) — see session.ts's comment
// for why this is the correct, verified way to test a next-auth-protected
// route outside a real running Next.js server. Default: an owner_manager
// session, so every pre-existing test below (whose actual purpose is
// upload validation + analysis, Report FR-1 — not the auth boundary
// itself) keeps testing exactly what it always tested. The dedicated
// auth-boundary tests further down override this per-test.
vi.mock("next-auth", () => ({ getServerSession: vi.fn() }));
import { getServerSession } from "next-auth";
import { POST } from "../route";
import { checkDbAvailable } from "@/db/dbAvailable";

const DB_AVAILABLE = await checkDbAvailable();

const SAMPLE_CSV_PATH = path.join(__dirname, "../../../../data/retail_inventory.csv");

function mockSession(role: "owner_manager" | "staff" | null) {
  vi.mocked(getServerSession).mockResolvedValue(role ? ({ user: { id: "1", role } } as never) : null);
}

function makeUploadRequest(fileContent: string, fileName = "test.csv"): Request {
  const formData = new FormData();
  const file = new File([fileContent], fileName, { type: "text/csv" });
  formData.append("file", file);
  return new Request("http://localhost/api/upload", { method: "POST", body: formData });
}

describe("POST /api/upload — auth boundary (Report FR-9: owner_manager only)", () => {
  it("returns 401 when there is no session at all", async () => {
    mockSession(null);
    const response = await POST(makeUploadRequest("sku,product_name\nX,Y"));
    expect(response.status).toBe(401);
  });

  it("returns 403 for a staff session (upload is a manager action, not a staff one)", async () => {
    mockSession("staff");
    const response = await POST(makeUploadRequest("sku,product_name\nX,Y"));
    expect(response.status).toBe(403);
    const body = await response.json();
    expect(body.error).toMatch(/owner_manager/);
  });
});

// This first suite's scope is upload validation + analysis (Report FR-1),
// not persistence — that's src/db/__tests__/repository.test.ts's job,
// tested directly against the real database there. DATABASE_URL is
// deliberately unset for the duration of its tests (see the beforeAll/
// afterAll nested inside it below): the global vitest.config.mts env
// loading otherwise makes the route's `if (process.env.DATABASE_URL)`
// persistence branch fire here too, which would (a) silently test
// something this suite never asserts on, and (b) since Vitest runs test
// files in parallel by default, race against repository.test.ts's
// TRUNCATE-based cleanup on the same real database — a genuine
// intermittent-failure risk, not merely untidy.
describe("POST /api/upload", () => {
  beforeEach(() => mockSession("owner_manager"));

  // Scoped to THIS describe block only (not the whole file): Vitest/Jest
  // hooks nest by block, and root-level hooks would instead wrap the
  // entire file — including the second describe block below — which
  // would leave DATABASE_URL deleted for that block's tests too (verified
  // by reasoning through the execution order before writing this, not
  // assumed). Scoping it here means it's restored before the next
  // describe block runs, since Vitest runs describe blocks within one
  // file sequentially by default.
  let savedDatabaseUrl: string | undefined;
  beforeAll(() => {
    savedDatabaseUrl = process.env.DATABASE_URL;
    delete process.env.DATABASE_URL;
  });
  afterAll(() => {
    if (savedDatabaseUrl !== undefined) process.env.DATABASE_URL = savedDatabaseUrl;
  });

  it("analyzes the real sample CSV via an actual multipart request and matches the report's numbers", async () => {
    const csvText = readFileSync(SAMPLE_CSV_PATH, "utf-8");
    const response = await POST(makeUploadRequest(csvText, "retail_inventory.csv"));
    expect(response.status).toBe(200);

    const body = await response.json();
    expect(body.skuCount).toBe(50);
    expect(body.rejectedRowCount).toBe(0);
    expect(body.kpis.totalInventoryValue).toBeCloseTo(21913.5, 1);
    expect(body.kpis.totalRevenue30d).toBeCloseTo(60356.0, 1);

    const fsnCounts: Record<string, number> = {};
    for (const row of body.fsn) fsnCounts[row.fsn_class] = row.skuCount;
    expect(fsnCounts["Fast-moving"]).toBe(10);
    expect(fsnCounts["Slow-moving"]).toBe(18);
    expect(fsnCounts["Non-moving"]).toBe(22);

    expect(body.reorderRisk.length).toBe(7);
  });

  it("returns 400 when no file field is present", async () => {
    const formData = new FormData();
    formData.append("not_the_file_field", "hello");
    const request = new Request("http://localhost/api/upload", { method: "POST", body: formData });
    const response = await POST(request);
    expect(response.status).toBe(400);
    const body = await response.json();
    expect(body.error).toMatch(/no file/i);
  });

  it("returns 400 for an empty file", async () => {
    const response = await POST(makeUploadRequest(""));
    expect(response.status).toBe(400);
    const body = await response.json();
    expect(body.error).toMatch(/empty/i);
  });

  it("returns 400 with a clear message when a required column is missing from the header", async () => {
    const badCsv = ["sku,product_name", "SKU1,Test"].join("\n");
    const response = await POST(makeUploadRequest(badCsv));
    expect(response.status).toBe(400);
    const body = await response.json();
    expect(body.error).toMatch(/missing required column/i);
  });

  it("returns 422 when every row is rejected (nothing left to analyze)", async () => {
    const allBadCsv = [
      "sku,product_name,category,size,color,quantity_on_hand,reorder_point,cost_per_unit,retail_price,last_restock_date,units_sold_30d,supplier,season",
      "SKU1,,Tops,S,Red,10,5,1.00,2.00,2024-01-01,3,Acme,Year-Round", // missing product_name
    ].join("\n");
    const response = await POST(makeUploadRequest(allBadCsv));
    expect(response.status).toBe(422);
    const body = await response.json();
    expect(body.error).toMatch(/every row/i);
    expect(body.rejected.length).toBe(1);
  });

  it("still returns results (200) alongside a non-zero rejectedRowCount for a partially-bad file", async () => {
    const mixedCsv = [
      "sku,product_name,category,size,color,quantity_on_hand,reorder_point,cost_per_unit,retail_price,last_restock_date,units_sold_30d,supplier,season",
      "SKU1,Good Row,Tops,S,Red,10,5,1.00,2.00,2024-01-01,3,Acme,Year-Round",
      "SKU2,,Tops,M,Blue,10,5,1.00,2.00,2024-01-01,3,Acme,Year-Round", // missing product_name
    ].join("\n");
    const response = await POST(makeUploadRequest(mixedCsv));
    expect(response.status).toBe(200);
    const body = await response.json();
    expect(body.skuCount).toBe(1);
    expect(body.rejectedRowCount).toBe(1);
  });

  it("returns datasetId: null and newlyAtRisk: null when no database is configured (Phase 2 is optional, not required)", async () => {
    const csvText = readFileSync(SAMPLE_CSV_PATH, "utf-8");
    const response = await POST(makeUploadRequest(csvText, "retail_inventory.csv"));
    const body = await response.json();
    expect(body.datasetId).toBeNull();
    expect(body.newlyAtRisk).toBeNull();
  });

  it("handles a realistic 10,000-SKU file through the full multipart request path (end-to-end, not just the underlying function)", async () => {
    const csv = generateSyntheticInventoryCsv({ count: 10000 });
    expect(new TextEncoder().encode(csv).length).toBeLessThan(4 * 1024 * 1024); // sanity: under this route's own cap

    const start = performance.now();
    const response = await POST(makeUploadRequest(csv, "large_catalog.csv"));
    const elapsedMs = performance.now() - start;

    expect(response.status).toBe(200);
    const body = await response.json();
    expect(body.skuCount).toBe(10000);
    expect(body.rejectedRowCount).toBe(0);
    expect(Number.isFinite(body.kpis.totalInventoryValue)).toBe(true);
    expect(elapsedMs).toBeLessThan(15000);
  });
});

// Separate describe block, deliberately isolated from the suite above:
// this is the one place that verifies the /api/upload route's persistence
// *wiring* itself (does it actually call saveAnalysisResult and return a
// real datasetId?) — not persistence correctness, which is
// repository.test.ts's job against the same real database. DATABASE_URL
// is scoped to only this block's lifetime, and the row it creates is
// explicitly deleted afterward so this file leaves no residue regardless
// of test-file execution order.
describe("POST /api/upload — persistence wiring (DB configured)", () => {
  beforeEach(() => mockSession("owner_manager"));

  let blockSavedDatabaseUrl: string | undefined;
  const createdDatasetIds: number[] = [];

  beforeAll(() => {
    // Just records whatever is currently set (for exact restoration in
    // afterAll) — deliberately not throwing if it's absent. Whether the
    // one test below actually runs is entirely `it.skipIf`'s job, evaluated
    // separately at describe-collection time (before any beforeAll runs),
    // so this hook has no assumption to enforce either way.
    blockSavedDatabaseUrl = process.env.DATABASE_URL;
  });

  afterAll(async () => {
    if (createdDatasetIds.length > 0) {
      const { getDb } = await import("@/db/client");
      const { datasets } = await import("@/db/schema");
      const { inArray } = await import("drizzle-orm");
      await getDb().delete(datasets).where(inArray(datasets.id, createdDatasetIds));
    }
    if (blockSavedDatabaseUrl !== undefined) process.env.DATABASE_URL = blockSavedDatabaseUrl;
  });

  it.skipIf(!DB_AVAILABLE)(
    "persists the uploaded dataset and returns a real datasetId, loadable back with matching numbers",
    async () => {
      const csv = [
        "sku,product_name,category,size,color,quantity_on_hand,reorder_point,cost_per_unit,retail_price,last_restock_date,units_sold_30d,supplier,season",
        "SKU1,Wiring Test Product,Tops,S,Red,10,5,1.00,2.00,2024-01-01,3,Acme,Year-Round",
      ].join("\n");

      const response = await POST(makeUploadRequest(csv, "wiring-test.csv"));
      expect(response.status).toBe(200);
      const body = await response.json();
      expect(typeof body.datasetId).toBe("number");
      createdDatasetIds.push(body.datasetId);

      const { loadDataset } = await import("@/db/repository");
      const reloaded = await loadDataset(body.datasetId);
      expect(reloaded).not.toBeNull();
      expect(reloaded!.sourceLabel).toBe("wiring-test.csv");
      expect(reloaded!.rows.length).toBe(1);
      expect(reloaded!.rows[0].sku).toBe("SKU1");
    }
  );

  it.skipIf(!DB_AVAILABLE)(
    "Report FR-10: newlyAtRisk is null on a first upload, then correctly lists a SKU that crosses into Reorder Now on the next", async () => {
      const day1 = [
        "sku,product_name,category,size,color,quantity_on_hand,reorder_point,cost_per_unit,retail_price,last_restock_date,units_sold_30d,supplier,season",
        "ALERT_SKU,Alert Test Widget,Tops,S,Red,50,10,1.00,2.00,2024-01-01,5,Acme,Year-Round", // healthy
      ].join("\n");
      const response1 = await POST(makeUploadRequest(day1, "alert-day1.csv"));
      const body1 = await response1.json();
      createdDatasetIds.push(body1.datasetId);
      expect(body1.rows.find((r: { sku: string }) => r.sku === "ALERT_SKU").stock_status).toBe("Healthy");
      // newlyAtRisk is computed relative to whatever dataset existed before
      // this one in the whole test DB — not necessarily empty, since other
      // tests in this file may have left datasets behind. What matters is
      // ALERT_SKU specifically must not appear (it didn't exist before).
      expect(body1.newlyAtRisk.some((r: { sku: string }) => r.sku === "ALERT_SKU")).toBe(false);

      const day2 = [
        "sku,product_name,category,size,color,quantity_on_hand,reorder_point,cost_per_unit,retail_price,last_restock_date,units_sold_30d,supplier,season",
        "ALERT_SKU,Alert Test Widget,Tops,S,Red,2,10,1.00,2.00,2024-01-02,45,Acme,Year-Round", // sold through, now at risk
      ].join("\n");
      const response2 = await POST(makeUploadRequest(day2, "alert-day2.csv"));
      const body2 = await response2.json();
      createdDatasetIds.push(body2.datasetId);

      expect(body2.rows.find((r: { sku: string }) => r.sku === "ALERT_SKU").stock_status).toBe("Reorder Now");
      expect(body2.newlyAtRisk.map((r: { sku: string }) => r.sku)).toEqual(["ALERT_SKU"]);

      // Report FR-10, email half: RESEND_API_KEY/RESEND_ALERT_TO are not
      // set in this sandbox's .env.local (no real key exists to test
      // actual delivery against — see BUILD_NOTES.md), so emailAlert must
      // report a clean skip here, not a silent omission or a crash. The
      // integration logic itself (constructing the right call, handling
      // both of Resend's failure shapes) is separately, thoroughly
      // covered with a mocked Resend client in
      // src/lib/alerts/__tests__/sendNewlyAtRiskEmail.test.ts.
      expect(body2.emailAlert).toBeDefined();
      expect(body2.emailAlert.sent).toBe(false);
      expect(body2.emailAlert.skipReason).toMatch(/RESEND_API_KEY|RESEND_ALERT_TO/);
    }
  );
});

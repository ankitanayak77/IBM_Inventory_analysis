import { describe, it, expect, beforeAll, afterAll, beforeEach, vi } from "vitest";
import { sql } from "drizzle-orm";

// See src/app/api/upload/__tests__/route.test.ts's comment for why this
// mocking approach (not next/headers) is the correct way to test a
// next-auth-protected route outside a real running Next.js server.
vi.mock("next-auth", () => ({ getServerSession: vi.fn() }));
import { getServerSession } from "next-auth";
import { GET as getDatasets } from "../route";
import { GET as getDatasetById } from "../[id]/route";
import { getDb, _resetPoolForTests } from "@/db/client";
import { datasets } from "@/db/schema";
import { analyzeAndSave } from "@/db/repository";
import { checkDbAvailable } from "@/db/dbAvailable";

const DB_AVAILABLE = await checkDbAvailable();

function mockSession(role: "owner_manager" | "staff" | null) {
  vi.mocked(getServerSession).mockResolvedValue(role ? ({ user: { id: "1", role } } as never) : null);
}

function makeIdRequest(id: string) {
  return getDatasetById(new Request(`http://localhost/api/datasets/${id}`), {
    params: Promise.resolve({ id }),
  });
}

describe("GET /api/datasets and /api/datasets/[id] — auth boundary (Report FR-9)", () => {
  it("GET /api/datasets returns 401 with no session", async () => {
    mockSession(null);
    expect((await getDatasets()).status).toBe(401);
  });

  it("GET /api/datasets returns 403 for a staff session (history browsing is owner_manager only)", async () => {
    mockSession("staff");
    expect((await getDatasets()).status).toBe(403);
  });

  it("GET /api/datasets/[id] returns 401 with no session", async () => {
    mockSession(null);
    expect((await makeIdRequest("1")).status).toBe(401);
  });
});

describe.skipIf(!DB_AVAILABLE)("GET /api/datasets and /api/datasets/[id] — against a real Postgres database", () => {
  beforeAll(() => {
    _resetPoolForTests();
  });

  beforeEach(async () => {
    mockSession("owner_manager");
    await getDb().execute(sql`TRUNCATE TABLE ${datasets} RESTART IDENTITY CASCADE`);
  });

  afterAll(async () => {
    await getDb().execute(sql`TRUNCATE TABLE ${datasets} RESTART IDENTITY CASCADE`);
  });

  it("lists datasets most-recent-first via the real route handler", async () => {
    await analyzeAndSave(
      "sku,product_name,category,size,color,quantity_on_hand,reorder_point,cost_per_unit,retail_price,last_restock_date,units_sold_30d,supplier,season\nS1,P1,Tops,S,Red,10,5,1,2,2024-01-01,3,Acme,Year-Round",
      "first.csv"
    );
    await analyzeAndSave(
      "sku,product_name,category,size,color,quantity_on_hand,reorder_point,cost_per_unit,retail_price,last_restock_date,units_sold_30d,supplier,season\nS2,P2,Tops,S,Red,10,5,1,2,2024-01-01,3,Acme,Year-Round",
      "second.csv"
    );

    const response = await getDatasets();
    expect(response.status).toBe(200);
    const body = await response.json();
    expect(body.databaseConfigured).toBe(true);
    expect(body.datasets.length).toBe(2);
    expect(body.datasets[0].sourceLabel).toBe("second.csv");
    expect(body.datasets[1].sourceLabel).toBe("first.csv");
  });

  it("loads one dataset by id with the full AnalysisResult shape for an owner_manager", async () => {
    const { datasetId } = await analyzeAndSave(
      "sku,product_name,category,size,color,quantity_on_hand,reorder_point,cost_per_unit,retail_price,last_restock_date,units_sold_30d,supplier,season\nS1,Widget,Tops,S,Red,10,5,1,2,2024-01-01,3,Acme,Year-Round",
      "widget.csv"
    );

    const response = await makeIdRequest(String(datasetId));
    expect(response.status).toBe(200);
    const body = await response.json();
    expect(body.sourceLabel).toBe("widget.csv");
    expect(body.rows.length).toBe(1);
    expect(body.rows[0].sku).toBe("S1");
    expect(body.kpis).toBeDefined();
    expect(body.fsn).toBeDefined();
  });

  it("loads the restricted staff view (reorder task list only, no KPIs/rows) for a staff session", async () => {
    const { datasetId } = await analyzeAndSave(
      "sku,product_name,category,size,color,quantity_on_hand,reorder_point,cost_per_unit,retail_price,last_restock_date,units_sold_30d,supplier,season\nS1,Understocked Item,Tops,S,Red,2,10,1,2,2024-01-01,20,Acme,Year-Round",
      "staff-view-test.csv"
    );

    mockSession("staff");
    const response = await makeIdRequest(String(datasetId));
    expect(response.status).toBe(200);
    const body = await response.json();
    expect(body.role).toBe("staff");
    expect(body.sourceLabel).toBe("staff-view-test.csv");
    expect(body.reorderRisk.length).toBe(1);
    expect(body.kpis).toBeUndefined();
    expect(body.fsn).toBeUndefined();
    expect(body.rows).toBeUndefined();
  });

  it("returns 404 for a dataset id that doesn't exist", async () => {
    const response = await makeIdRequest("999999");
    expect(response.status).toBe(404);
  });

  it("returns 400 for a non-numeric id", async () => {
    const response = await makeIdRequest("not-a-number");
    expect(response.status).toBe(400);
  });
});

describe("GET /api/datasets and /api/datasets/[id] — no database configured", () => {
  let saved: string | undefined;
  beforeAll(() => {
    saved = process.env.DATABASE_URL;
    delete process.env.DATABASE_URL;
  });
  beforeEach(() => mockSession("owner_manager"));
  afterAll(() => {
    if (saved !== undefined) process.env.DATABASE_URL = saved;
  });

  it("GET /api/datasets returns an empty list with databaseConfigured: false, not an error", async () => {
    const response = await getDatasets();
    expect(response.status).toBe(200);
    const body = await response.json();
    expect(body.datasets).toEqual([]);
    expect(body.databaseConfigured).toBe(false);
  });

  it("GET /api/datasets/[id] returns 503 with a clear message, not a crash", async () => {
    const response = await makeIdRequest("1");
    expect(response.status).toBe(503);
    const body = await response.json();
    expect(body.error).toMatch(/no database/i);
  });
});

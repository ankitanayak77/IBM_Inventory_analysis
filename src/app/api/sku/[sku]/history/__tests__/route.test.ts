import { describe, it, expect, beforeAll, afterAll, beforeEach, vi } from "vitest";
import { sql } from "drizzle-orm";

// See src/app/api/upload/__tests__/route.test.ts's comment for why this
// mocking approach (not next/headers) is the correct way to test a
// next-auth-protected route outside a real running Next.js server.
vi.mock("next-auth", () => ({ getServerSession: vi.fn() }));
import { getServerSession } from "next-auth";
import { GET } from "../route";
import { getDb, _resetPoolForTests } from "@/db/client";
import { datasets } from "@/db/schema";
import { analyzeAndSave } from "@/db/repository";
import { checkDbAvailable } from "@/db/dbAvailable";

const DB_AVAILABLE = await checkDbAvailable();

function mockSession(role: "owner_manager" | "staff" | null) {
  vi.mocked(getServerSession).mockResolvedValue(role ? ({ user: { id: "1", role } } as never) : null);
}

function makeSkuRequest(sku: string) {
  return GET(new Request(`http://localhost/api/sku/${sku}/history`), { params: Promise.resolve({ sku }) });
}

describe("GET /api/sku/[sku]/history — auth boundary (Report FR-9)", () => {
  it("returns 401 when there is no session", async () => {
    mockSession(null);
    expect((await makeSkuRequest("X")).status).toBe(401);
  });

  it("returns 403 for a staff session (SKU drill-down is owner_manager only)", async () => {
    mockSession("staff");
    expect((await makeSkuRequest("X")).status).toBe(403);
  });
});

describe.skipIf(!DB_AVAILABLE)("GET /api/sku/[sku]/history — against a real Postgres database", () => {
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

  it("returns an empty history for a SKU that was never uploaded", async () => {
    const response = await makeSkuRequest("NEVER_EXISTED");
    expect(response.status).toBe(200);
    const body = await response.json();
    expect(body.databaseConfigured).toBe(true);
    expect(body.history).toEqual([]);
  });

  it("returns the real historical trend across multiple real uploads, through the actual route", async () => {
    await analyzeAndSave(
      "sku,product_name,category,size,color,quantity_on_hand,reorder_point,cost_per_unit,retail_price,last_restock_date,units_sold_30d,supplier,season\nTREND_SKU,Widget,Tops,S,Red,50,10,1,2,2024-01-01,5,Acme,Year-Round",
      "trend-day1.csv"
    );
    await analyzeAndSave(
      "sku,product_name,category,size,color,quantity_on_hand,reorder_point,cost_per_unit,retail_price,last_restock_date,units_sold_30d,supplier,season\nTREND_SKU,Widget,Tops,S,Red,3,10,1,2,2024-01-08,40,Acme,Year-Round",
      "trend-day2.csv"
    );

    const response = await makeSkuRequest("TREND_SKU");
    expect(response.status).toBe(200);
    const body = await response.json();
    expect(body.history.length).toBe(2);
    expect(body.history[0].sourceLabel).toBe("trend-day1.csv");
    expect(body.history[0].record.stock_status).toBe("Healthy");
    expect(body.history[1].sourceLabel).toBe("trend-day2.csv");
    expect(body.history[1].record.stock_status).toBe("Reorder Now");
  });
});

describe("GET /api/sku/[sku]/history — no database configured", () => {
  let saved: string | undefined;
  beforeAll(() => {
    saved = process.env.DATABASE_URL;
    delete process.env.DATABASE_URL;
  });
  beforeEach(() => mockSession("owner_manager"));
  afterAll(() => {
    if (saved !== undefined) process.env.DATABASE_URL = saved;
  });

  it("returns an empty history with databaseConfigured: false, not an error", async () => {
    const response = await makeSkuRequest("X");
    expect(response.status).toBe(200);
    const body = await response.json();
    expect(body.history).toEqual([]);
    expect(body.databaseConfigured).toBe(false);
  });
});

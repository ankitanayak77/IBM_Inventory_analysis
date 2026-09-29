import { describe, it, expect, beforeAll, afterAll, beforeEach } from "vitest";
import { readFileSync } from "fs";
import path from "path";
import { sql } from "drizzle-orm";
import { getDb, _resetPoolForTests } from "../client";
import { datasets, skuRecords } from "../schema";
import { saveAnalysisResult, listDatasets, loadDataset, analyzeAndSave, getPreviousDatasetRows, getSkuHistory } from "../repository";
import { analyzeCsvText } from "@/lib/analytics/analyze";

/**
 * These tests run against a REAL local Postgres 16 instance (installed
 * via apt in this sandbox — see the conversation for exact commands),
 * not a mock. This is deliberate: mocking the database layer would only
 * prove the mock behaves as programmed, not that the actual SQL, the
 * actual Drizzle column types, and the actual Infinity-safe numeric
 * round-trip (see schema.ts's comment) genuinely work.
 *
 * Requires DATABASE_URL to be set (see .env.local) and a running local
 * (e.g. a fresh clone of this repo, or a CI runner without it configured).
 */

import { checkDbAvailable } from "../dbAvailable";

const DB_AVAILABLE = await checkDbAvailable();

describe.skipIf(!DB_AVAILABLE)("repository — persistence against a real Postgres database", () => {
  beforeAll(() => {
    _resetPoolForTests();
  });

  beforeEach(async () => {
    // Clean slate between tests — cascade delete means clearing datasets
    // also clears sku_records (the FK is ON DELETE CASCADE).
    const db = getDb();
    await db.execute(sql`TRUNCATE TABLE ${datasets} RESTART IDENTITY CASCADE`);
  });

  afterAll(async () => {
    const db = getDb();
    await db.execute(sql`TRUNCATE TABLE ${datasets} RESTART IDENTITY CASCADE`);
  });

  it("saves the real report-verified sample dataset and reads it back with identical numbers", async () => {
    const csvPath = path.join(process.cwd(), "src/data/retail_inventory.csv");
    const original = analyzeCsvText(readFileSync(csvPath, "utf-8"));

    const { datasetId } = await saveAnalysisResult(original, "sample dataset");
    expect(datasetId).toBeGreaterThan(0);

    const reloaded = await loadDataset(datasetId);
    expect(reloaded).not.toBeNull();
    expect(reloaded!.sourceLabel).toBe("sample dataset");
    expect(reloaded!.rows.length).toBe(50);

    // Exact parity with the report's verified numbers (Sections 4.1-4.5),
    // now round-tripped through a real database, not just computed in memory.
    expect(reloaded!.kpis.totalInventoryValue).toBeCloseTo(21913.5, 1);
    expect(reloaded!.kpis.totalRevenue30d).toBeCloseTo(60356.0, 1);
    const fsnCounts: Record<string, number> = {};
    for (const f of reloaded!.fsn) fsnCounts[f.fsn_class] = f.skuCount;
    expect(fsnCounts["Fast-moving"]).toBe(10);
    expect(fsnCounts["Slow-moving"]).toBe(18);
    expect(fsnCounts["Non-moving"]).toBe(22);
    expect(reloaded!.reorderRisk.length).toBe(7);
  });

  it("REGRESSION: correctly round-trips Infinity through the real database, not null", async () => {
    // The exact edge case discovered during load-testing (Step 4): a SKU
    // stocked out but with recorded sales gets itr_annualised = Infinity.
    const csv = [
      "sku,product_name,category,size,color,quantity_on_hand,reorder_point,cost_per_unit,retail_price,last_restock_date,units_sold_30d,supplier,season",
      "SKU1,Stocked Out Bestseller,Tops,S,Red,0,5,10.00,20.00,2024-01-01,15,Acme,Year-Round",
    ].join("\n");

    const original = analyzeCsvText(csv);
    expect(original.rows[0].itr_annualised).toBe(Infinity); // sanity on the input itself

    const { datasetId } = await saveAnalysisResult(original, "infinity-test.csv");
    const reloaded = await loadDataset(datasetId);

    expect(reloaded!.rows[0].itr_annualised).toBe(Infinity);
    expect(Number.isNaN(reloaded!.rows[0].itr_annualised)).toBe(false);
    expect(reloaded!.rows[0].days_of_stock).toBe(0);
  });

  it("lists saved datasets most-recent-first", async () => {
    await analyzeAndSave(
      "sku,product_name,category,size,color,quantity_on_hand,reorder_point,cost_per_unit,retail_price,last_restock_date,units_sold_30d,supplier,season\nS1,P1,Tops,S,Red,10,5,1,2,2024-01-01,3,Acme,Year-Round",
      "first-upload.csv"
    );
    await analyzeAndSave(
      "sku,product_name,category,size,color,quantity_on_hand,reorder_point,cost_per_unit,retail_price,last_restock_date,units_sold_30d,supplier,season\nS2,P2,Tops,S,Red,10,5,1,2,2024-01-01,3,Acme,Year-Round",
      "second-upload.csv"
    );

    const list = await listDatasets();
    expect(list.length).toBe(2);
    expect(list[0].sourceLabel).toBe("second-upload.csv"); // most recent first
    expect(list[1].sourceLabel).toBe("first-upload.csv");
    expect(list[0].skuCount).toBe(1);
  });

  it("returns null for a dataset id that doesn't exist", async () => {
    const result = await loadDataset(999999);
    expect(result).toBeNull();
  });

  it("cascades delete: removing a dataset removes its sku_records too", async () => {
    const { datasetId } = await analyzeAndSave(
      "sku,product_name,category,size,color,quantity_on_hand,reorder_point,cost_per_unit,retail_price,last_restock_date,units_sold_30d,supplier,season\nS1,P1,Tops,S,Red,10,5,1,2,2024-01-01,3,Acme,Year-Round",
      "to-delete.csv"
    );
    const db = getDb();
    let records = await db.select().from(skuRecords);
    expect(records.length).toBe(1);

    await db.delete(datasets).where(sql`${datasets.id} = ${datasetId}`);

    records = await db.select().from(skuRecords);
    expect(records.length).toBe(0); // cascaded, not orphaned
  });

  it("persists and reloads the full 10,000-SKU synthetic catalog without error", async () => {
    const { generateSyntheticInventoryCsv } = await import("@/test-fixtures/generateSyntheticInventory");
    const csv = generateSyntheticInventoryCsv({ count: 10000 });

    const start = performance.now();
    const { datasetId } = await analyzeAndSave(csv, "large_catalog.csv");
    const reloaded = await loadDataset(datasetId);
    const elapsedMs = performance.now() - start;

    expect(reloaded!.rows.length).toBe(10000);
    expect(elapsedMs).toBeLessThan(15000);
  });

  it("getPreviousDatasetRows returns null for the very first dataset ever saved", async () => {
    const { datasetId } = await analyzeAndSave(
      "sku,product_name,category,size,color,quantity_on_hand,reorder_point,cost_per_unit,retail_price,last_restock_date,units_sold_30d,supplier,season\nS1,P1,Tops,S,Red,10,5,1,2,2024-01-01,3,Acme,Year-Round",
      "only-upload.csv"
    );
    expect(await getPreviousDatasetRows(datasetId)).toBeNull();
  });

  it("getPreviousDatasetRows returns null for a dataset id that doesn't exist", async () => {
    expect(await getPreviousDatasetRows(999999)).toBeNull();
  });

  it("getPreviousDatasetRows returns the immediately-preceding dataset's rows by upload order, not save order", async () => {
    const { datasetId: firstId } = await analyzeAndSave(
      "sku,product_name,category,size,color,quantity_on_hand,reorder_point,cost_per_unit,retail_price,last_restock_date,units_sold_30d,supplier,season\nFIRST,P1,Tops,S,Red,10,5,1,2,2024-01-01,3,Acme,Year-Round",
      "first.csv"
    );
    const { datasetId: secondId } = await analyzeAndSave(
      "sku,product_name,category,size,color,quantity_on_hand,reorder_point,cost_per_unit,retail_price,last_restock_date,units_sold_30d,supplier,season\nSECOND,P2,Tops,S,Red,10,5,1,2,2024-01-01,3,Acme,Year-Round",
      "second.csv"
    );
    const { datasetId: thirdId } = await analyzeAndSave(
      "sku,product_name,category,size,color,quantity_on_hand,reorder_point,cost_per_unit,retail_price,last_restock_date,units_sold_30d,supplier,season\nTHIRD,P3,Tops,S,Red,10,5,1,2,2024-01-01,3,Acme,Year-Round",
      "third.csv"
    );

    expect(await getPreviousDatasetRows(firstId)).toBeNull();

    const beforeSecond = await getPreviousDatasetRows(secondId);
    expect(beforeSecond?.[0]?.sku).toBe("FIRST");

    const beforeThird = await getPreviousDatasetRows(thirdId);
    expect(beforeThird?.[0]?.sku).toBe("SECOND");
  });

  it("end-to-end: findNewlyAtRisk over two real, sequentially-saved datasets correctly identifies the transition", async () => {
    const { findNewlyAtRisk } = await import("@/lib/analytics/compareDatasets");

    // Day 1: SKU X is healthy (plenty of stock, modest sales).
    const { datasetId: day1Id } = await analyzeAndSave(
      "sku,product_name,category,size,color,quantity_on_hand,reorder_point,cost_per_unit,retail_price,last_restock_date,units_sold_30d,supplier,season\nX,Widget,Tops,S,Red,50,10,1,2,2024-01-01,5,Acme,Year-Round",
      "day1.csv"
    );
    // Day 2: SKU X has sold through and is now below its reorder point.
    const { datasetId: day2Id, result: day2Result } = await analyzeAndSave(
      "sku,product_name,category,size,color,quantity_on_hand,reorder_point,cost_per_unit,retail_price,last_restock_date,units_sold_30d,supplier,season\nX,Widget,Tops,S,Red,3,10,1,2,2024-01-02,40,Acme,Year-Round",
      "day2.csv"
    );

    expect(day2Result.rows[0].stock_status).toBe("Reorder Now"); // sanity on the fixture itself
    void day1Id;

    const previousRows = await getPreviousDatasetRows(day2Id);
    const newlyAtRisk = findNewlyAtRisk(previousRows, day2Result.rows);

    expect(newlyAtRisk.map((r) => r.sku)).toEqual(["X"]);
  });

  it("getSkuHistory returns an empty array for a SKU that was never uploaded", async () => {
    expect(await getSkuHistory("NEVER_EXISTED_SKU")).toEqual([]);
  });

  it("getSkuHistory returns every historical record for a SKU across multiple datasets, oldest first", async () => {
    const { datasetId: day1Id } = await analyzeAndSave(
      "sku,product_name,category,size,color,quantity_on_hand,reorder_point,cost_per_unit,retail_price,last_restock_date,units_sold_30d,supplier,season\nHIST_SKU,Widget,Tops,S,Red,50,10,1,2,2024-01-01,5,Acme,Year-Round",
      "hist-day1.csv"
    );
    const { datasetId: day2Id } = await analyzeAndSave(
      "sku,product_name,category,size,color,quantity_on_hand,reorder_point,cost_per_unit,retail_price,last_restock_date,units_sold_30d,supplier,season\nHIST_SKU,Widget,Tops,S,Red,30,10,1,2,2024-01-08,20,Acme,Year-Round",
      "hist-day2.csv"
    );
    const { datasetId: day3Id } = await analyzeAndSave(
      "sku,product_name,category,size,color,quantity_on_hand,reorder_point,cost_per_unit,retail_price,last_restock_date,units_sold_30d,supplier,season\nHIST_SKU,Widget,Tops,S,Red,3,10,1,2,2024-01-15,40,Acme,Year-Round",
      "hist-day3.csv"
    );

    const history = await getSkuHistory("HIST_SKU");
    expect(history.length).toBe(3);
    expect(history.map((h) => h.datasetId)).toEqual([day1Id, day2Id, day3Id]); // oldest first, matching upload order
    expect(history.map((h) => h.sourceLabel)).toEqual(["hist-day1.csv", "hist-day2.csv", "hist-day3.csv"]);
    expect(history.map((h) => h.record.quantity_on_hand)).toEqual([50, 30, 3]); // the actual stock trend
    expect(history[0].record.stock_status).toBe("Healthy");
    expect(history[2].record.stock_status).toBe("Reorder Now"); // the trend that matters: it declined into risk
  });

  it("getSkuHistory only returns records for the requested SKU, not other SKUs in the same datasets", async () => {
    await analyzeAndSave(
      "sku,product_name,category,size,color,quantity_on_hand,reorder_point,cost_per_unit,retail_price,last_restock_date,units_sold_30d,supplier,season\nSKU_A,Widget A,Tops,S,Red,10,5,1,2,2024-01-01,3,Acme,Year-Round\nSKU_B,Widget B,Tops,M,Blue,10,5,1,2,2024-01-01,3,Acme,Year-Round",
      "multi-sku.csv"
    );
    const historyA = await getSkuHistory("SKU_A");
    expect(historyA.length).toBe(1);
    expect(historyA[0].record.sku).toBe("SKU_A");
  });
});

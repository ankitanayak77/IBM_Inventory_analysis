import { describe, it, expect } from "vitest";
import { generateSyntheticInventoryCsv } from "../../../test-fixtures/generateSyntheticInventory";
import { parseInventoryCsv } from "../parseCsv";
import { classifyInventory } from "../classify";
import {
  computePortfolioKpis,
  computeFsnBreakdown,
  computeAbcBreakdown,
  computeReorderRiskList,
  computeProductParetoRollup,
  computeCategoryPerformance,
  computeFsnAbcMatrix,
} from "../summary";

/**
 * Report NFR (Section 6.2): "Classification job for a 10,000-SKU catalog
 * completes in under 2 minutes on a single small server instance." This
 * suite is the actual evidence for that claim — previously it was an
 * unverified assumption written into the report and BUILD_NOTES. Measured
 * on this sandbox: ~530ms, i.e. roughly 220x under budget. The 15-second
 * threshold below is deliberately generous (this sandbox's CPU is not
 * guaranteed comparable to "a single small server instance") while still
 * being tight enough to catch a real performance regression.
 *
 * This suite is also where the zero-quantity-on-hand edge case first
 * surfaced — never present in the 50-row report sample, but ~1.65% of a
 * realistic 10,000-SKU catalog — which was producing NaN and corrupting
 * the FSN ranking until classify.ts's withDerivedMetrics was fixed. The
 * regression tests below pin that fix down explicitly.
 */
describe("classifyInventory — performance and correctness at 10,000-SKU scale", () => {
  it("parses and classifies 10,000 SKUs well within the Report NFR budget (<2 minutes)", () => {
    const csv = generateSyntheticInventoryCsv({ count: 10000 });

    const start = performance.now();
    const { rows, rejected } = parseInventoryCsv(csv);
    const classified = classifyInventory(rows);
    const elapsedMs = performance.now() - start;

    expect(rows.length).toBe(10000);
    expect(rejected.length).toBe(0);
    expect(classified.length).toBe(10000);
    expect(elapsedMs).toBeLessThan(15000); // generous vs. the report's 120,000ms NFR
  });

  it("produces zero NaN / non-finite values that would corrupt sorting or display", () => {
    const csv = generateSyntheticInventoryCsv({ count: 10000 });
    const { rows } = parseInventoryCsv(csv);
    const classified = classifyInventory(rows);

    const nanCount = classified.filter((r) => Number.isNaN(r.itr_annualised) || Number.isNaN(r.days_of_stock)).length;
    expect(nanCount).toBe(0);
  });

  it("classifies every SKU into a valid FSN and ABC class, and counts sum to the total", () => {
    const csv = generateSyntheticInventoryCsv({ count: 10000 });
    const { rows } = parseInventoryCsv(csv);
    const classified = classifyInventory(rows);

    const validFsn = ["Fast-moving", "Slow-moving", "Non-moving"];
    const validAbc = ["A", "B", "C"];
    expect(classified.every((r) => validFsn.includes(r.fsn_class))).toBe(true);
    expect(classified.every((r) => validAbc.includes(r.abc_class))).toBe(true);

    // The SKU-share method (Report Section 3.2, point 2) targets 20% / 35% / 45%
    // by count — confirm that holds at this larger, more varied scale too, not
    // just on the 50-row sample where it was originally verified.
    const fsn = computeFsnBreakdown(classified);
    const byClass = new Map(fsn.map((f) => [f.fsn_class, f.skuCount]));
    expect(byClass.get("Fast-moving")).toBe(2000);
    expect(byClass.get("Slow-moving")).toBe(3500);
    expect(byClass.get("Non-moving")).toBe(4500);
  });

  it("all downstream aggregations run without throwing at 10,000-SKU scale", () => {
    const csv = generateSyntheticInventoryCsv({ count: 10000 });
    const { rows } = parseInventoryCsv(csv);
    const classified = classifyInventory(rows);

    expect(() => computePortfolioKpis(classified)).not.toThrow();
    expect(() => computeFsnBreakdown(classified)).not.toThrow();
    expect(() => computeAbcBreakdown(classified)).not.toThrow();
    expect(() => computeReorderRiskList(classified)).not.toThrow();
    expect(() => computeProductParetoRollup(classified)).not.toThrow();
    expect(() => computeCategoryPerformance(classified)).not.toThrow();
    expect(() => computeFsnAbcMatrix(classified)).not.toThrow();

    const kpis = computePortfolioKpis(classified);
    expect(Number.isFinite(kpis.totalInventoryValue)).toBe(true);
    expect(Number.isFinite(kpis.totalRevenue30d)).toBe(true);
    expect(Number.isFinite(kpis.medianItr)).toBe(true);
  });

  it("REGRESSION: a SKU with 0 stock and 0 sales gets itr=0 and days_of_stock=0, not NaN/Infinity", () => {
    const csv = [
      "sku,product_name,category,size,color,quantity_on_hand,reorder_point,cost_per_unit,retail_price,last_restock_date,units_sold_30d,supplier,season",
      "SKU1,Zero Everything,Tops,S,Red,0,5,10.00,20.00,2024-01-01,0,Acme,Year-Round",
    ].join("\n");
    const { rows } = parseInventoryCsv(csv);
    const [classified] = classifyInventory(rows);

    expect(classified.itr_annualised).toBe(0);
    expect(classified.days_of_stock).toBe(0);
    expect(classified.stock_status).toBe("Reorder Now");
    // n=1: fastCut=round(0.2)=0, slowCut=round(0.55)=1 → rank 1 falls in
    // the Slow-moving band (verified directly, not assumed — see conversation).
    expect(classified.fsn_class).toBe("Slow-moving");
  });

  it("REGRESSION: a SKU with 0 stock but positive sales gets itr=Infinity (correctly the most urgent signal), not NaN", () => {
    const csv = [
      "sku,product_name,category,size,color,quantity_on_hand,reorder_point,cost_per_unit,retail_price,last_restock_date,units_sold_30d,supplier,season",
      "SKU1,Stocked Out Bestseller,Tops,S,Red,0,5,10.00,20.00,2024-01-01,15,Acme,Year-Round",
      "SKU2,Normal Item,Tops,M,Blue,10,5,10.00,20.00,2024-01-01,3,Acme,Year-Round",
    ].join("\n");
    const { rows } = parseInventoryCsv(csv);
    const classified = classifyInventory(rows);
    const skuOut = classified.find((r) => r.sku === "SKU1")!;

    expect(skuOut.itr_annualised).toBe(Infinity);
    expect(skuOut.days_of_stock).toBe(0); // already out — 0 days remaining, not Infinity
    expect(skuOut.stock_status).toBe("Reorder Now");
    expect(Number.isNaN(skuOut.itr_annualised)).toBe(false);
  });
});

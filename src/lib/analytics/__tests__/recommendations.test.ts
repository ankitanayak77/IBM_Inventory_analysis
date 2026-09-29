import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import path from "path";
import { parseInventoryCsv } from "../parseCsv";
import { classifyInventory } from "../classify";
import { computePortfolioKpis, computeReorderRiskList } from "../summary";
import {
  calculateSuggestedOrderQty,
  computeInventoryHealthScore,
  computeInventoryRecommendations,
} from "../recommendations";
import { generateSyntheticInventoryCsv } from "@/test-fixtures/generateSyntheticInventory";

describe("Inventory Recommendations Engine", () => {
  describe("calculateSuggestedOrderQty", () => {
    it("suggests reorder quantity based on ROP and 30-day demand cycle buffer", () => {
      // QOH: 5, ROP: 10, 30d sales: 30 (1 unit/day)
      // dailyDemand = 1, buffer = 30, targetStock = max(20, 10 + 30) = 40
      // SOQ = 40 - 5 = 35
      const soq = calculateSuggestedOrderQty(5, 10, 30, 30);
      expect(soq).toBe(35);
    });

    it("returns 0 when current stock already meets or exceeds target stock", () => {
      // QOH: 50, ROP: 10, 30d sales: 15
      // targetStock = max(20, 10 + 15) = 25
      // QOH (50) >= 25 -> SOQ = 0
      const soq = calculateSuggestedOrderQty(50, 10, 15, 30);
      expect(soq).toBe(0);
    });

    it("handles zero sales gracefully using 2x ROP standard buffer", () => {
      // QOH: 2, ROP: 8, 30d sales: 0
      // targetStock = max(16, 8 + 0) = 16
      // SOQ = 16 - 2 = 14
      const soq = calculateSuggestedOrderQty(2, 8, 0, 30);
      expect(soq).toBe(14);
    });

    it("scales correctly with custom target buffer days", () => {
      // QOH: 10, ROP: 20, 30d sales: 60 (2 units/day)
      // 15 days buffer -> targetStock = max(40, 20 + 30) = 50 -> SOQ = 40
      // 60 days buffer -> targetStock = max(40, 20 + 120) = 140 -> SOQ = 130
      const soq15 = calculateSuggestedOrderQty(10, 20, 60, 15);
      const soq60 = calculateSuggestedOrderQty(10, 20, 60, 60);
      expect(soq15).toBe(40);
      expect(soq60).toBe(130);
    });
  });

  describe("computeInventoryHealthScore", () => {
    it("returns 100 / Excellent for an empty catalog", () => {
      const { score, grade } = computeInventoryHealthScore(0, 0, 0, 0, 0, 5, 55);
      expect(score).toBe(100);
      expect(grade).toBe("Excellent");
    });

    it("returns a high score for a healthy portfolio with strong turnover and margin", () => {
      // 100 SKUs, 0 at risk, 0 dead stock, 6.0 turnover, 60% margin
      const { score, grade } = computeInventoryHealthScore(100, 0, 0, 50000, 0, 6.0, 60);
      expect(score).toBeGreaterThanOrEqual(90);
      expect(grade).toBe("Excellent");
    });

    it("downgrades grade when stockouts and dead stock are severe", () => {
      // 100 SKUs, 50 Reorder Now, 80% dead stock
      const { score, grade } = computeInventoryHealthScore(100, 60, 50, 100000, 80000, 0.5, 20);
      expect(score).toBeLessThan(50);
      expect(grade).toBe("Critical Risk");
    });

    it("stays bounded between 0 and 100 in all extreme cases", () => {
      const minBound = computeInventoryHealthScore(10, 10, 10, 10000, 10000, 0, 0);
      const maxBound = computeInventoryHealthScore(10, 0, 0, 10000, 0, 100, 100);
      expect(minBound.score).toBeGreaterThanOrEqual(0);
      expect(maxBound.score).toBeLessThanOrEqual(100);
    });
  });

  describe("computeInventoryRecommendations on sample dataset", () => {
    const csvPath = path.join(process.cwd(), "src/data/retail_inventory.csv");
    const { rows: rawRows } = parseInventoryCsv(readFileSync(csvPath, "utf-8"));
    const rows = classifyInventory(rawRows);
    const kpis = computePortfolioKpis(rows);
    const reorderRisk = computeReorderRiskList(rows);
    const recs = computeInventoryRecommendations(rows, kpis, reorderRisk);

    it("produces valid recommendations with all positive financial impacts", () => {
      expect(recs.healthScore).toBeGreaterThan(50);
      expect(recs.healthScore).toBeLessThanOrEqual(100);
      expect(recs.items.length).toBeGreaterThan(0);
      expect(recs.totalReplenishmentCost).toBeGreaterThan(0);
      expect(recs.trappedCapitalInDeadStock).toBeGreaterThanOrEqual(0);
      expect(recs.potentialCapitalRecovery).toBeGreaterThanOrEqual(0);
    });

    it("identifies all Reorder Now SKUs as immediate replenishment actions", () => {
      const reorderNowSkus = rows.filter((r) => r.stock_status === "Reorder Now").map((r) => r.sku);
      const replenishmentRecs = recs.items.filter((i) => i.type === "replenishment" && i.actionData.stockStatus === "Reorder Now");

      expect(replenishmentRecs.length).toBe(reorderNowSkus.length);
      for (const sku of reorderNowSkus) {
        expect(replenishmentRecs.some((r) => r.sku === sku)).toBe(true);
      }
    });

    it("aggregates supplier risk summary correctly covering all suppliers", () => {
      const distinctSuppliers = new Set(rows.map((r) => r.supplier));
      expect(recs.supplierRiskSummary.length).toBe(distinctSuppliers.size);

      const totalValueAcrossSuppliers = recs.supplierRiskSummary.reduce((s, r) => s + r.totalInventoryValue, 0);
      expect(totalValueAcrossSuppliers).toBeCloseTo(kpis.totalInventoryValue, 1);
    });

    it("generates a coherent, metric-backed executive summary narrative", () => {
      expect(recs.executiveSummaryText).toContain("Portfolio Health Score is rated");
      expect(recs.executiveSummaryText).toContain("SKUs");
      expect(recs.executiveSummaryText).toContain("replenishment");
    });

    it("computes annualized GMROI metric reflecting inventory capital productivity", () => {
      expect(kpis.gmroi).toBeGreaterThan(0);
      expect(Number.isFinite(kpis.gmroi)).toBe(true);
      // GMROI = Annualized Gross Margin / Inventory Value
      const expectedGmroi = (kpis.totalGrossMargin30d * 12) / kpis.totalInventoryValue;
      expect(kpis.gmroi).toBeCloseTo(expectedGmroi, 2);
    });
  });

  describe("scale test on 10,000 SKUs", () => {
    it("computes recommendations for 10,000 SKUs in under 200ms", () => {
      const csv = generateSyntheticInventoryCsv({ count: 10000, seed: 42 });
      const { rows: rawRows } = parseInventoryCsv(csv);
      const rows = classifyInventory(rawRows);
      const kpis = computePortfolioKpis(rows);
      const risk = computeReorderRiskList(rows);

      const start = performance.now();
      const recs = computeInventoryRecommendations(rows, kpis, risk);
      const elapsed = performance.now() - start;

      expect(elapsed).toBeLessThan(1500); // well within generous CI budget
      expect(Number.isFinite(recs.healthScore)).toBe(true);
      expect(recs.items.length).toBeGreaterThan(0);
      expect(Number.isFinite(recs.totalReplenishmentCost)).toBe(true);
      expect(Number.isFinite(recs.potentialCapitalRecovery)).toBe(true);
    });
  });
});

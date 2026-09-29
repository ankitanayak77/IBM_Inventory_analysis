import { describe, it, expect } from "vitest";
import Papa from "papaparse";
import { readFileSync } from "fs";
import path from "path";
import { parseInventoryCsv } from "@/lib/analytics/parseCsv";
import { classifyInventory } from "@/lib/analytics/classify";
import { rowsToCsv, recommendationsToCsv, supplierPoToCsv } from "../toCsv";
import { computePortfolioKpis, computeReorderRiskList } from "@/lib/analytics/summary";
import { computeInventoryRecommendations } from "@/lib/analytics/recommendations";

describe("rowsToCsv", () => {
  it("round-trips the real sample dataset: same row count, correct headers, parseable output", () => {
    const csvPath = path.join(process.cwd(), "src/data/retail_inventory.csv");
    const { rows } = parseInventoryCsv(readFileSync(csvPath, "utf-8"));
    const classified = classifyInventory(rows);

    const csvOut = rowsToCsv(classified);
    const reparsed = Papa.parse(csvOut, { header: true, skipEmptyLines: true });

    expect(reparsed.errors).toEqual([]);
    expect(reparsed.data.length).toBe(50);
    expect(Object.keys(reparsed.data[0] as object)).toContain("SKU");
    expect(Object.keys(reparsed.data[0] as object)).toContain("Priority");

    // Spot-check one known row against the report's verified numbers
    // (RET024, the single most urgent reorder — Report Section 4.5).
    const ret024 = (reparsed.data as Record<string, string>[]).find((r) => r.SKU === "RET024");
    expect(ret024).toBeDefined();
    expect(ret024!["Stock Status"]).toBe("Reorder Now");
    expect(ret024!["FSN Class"]).toBe("Fast-moving");
    expect(Number(ret024!["Qty On Hand"])).toBe(4);
  });

  it("produces a row count matching the input for a filtered (reorder-risk-only) list", () => {
    const csvPath = path.join(process.cwd(), "src/data/retail_inventory.csv");
    const { rows } = parseInventoryCsv(readFileSync(csvPath, "utf-8"));
    const classified = classifyInventory(rows);
    const reorderOnly = classified.filter((r) => r.stock_status !== "Healthy");

    const csvOut = rowsToCsv(reorderOnly);
    const reparsed = Papa.parse(csvOut, { header: true, skipEmptyLines: true });

    expect(reparsed.data.length).toBe(7); // matches Report Section 4.5's 7 at-risk SKUs
  });

  it("correctly escapes a product name containing a comma", () => {
    const csvPath = path.join(process.cwd(), "src/data/retail_inventory.csv");
    const { rows } = parseInventoryCsv(readFileSync(csvPath, "utf-8"));
    const classified = classifyInventory(rows);
    const withComma = { ...classified[0], product_name: "Shirt, Deluxe Edition" };

    const csvOut = rowsToCsv([withComma]);
    const reparsed = Papa.parse(csvOut, { header: true, skipEmptyLines: true });

    expect((reparsed.data[0] as Record<string, string>).Product).toBe("Shirt, Deluxe Edition");
  });

  it("returns just a header row for an empty list, without throwing", () => {
    expect(() => rowsToCsv([])).not.toThrow();
    const csvOut = rowsToCsv([]);
    expect(csvOut.split("\n")[0]).toContain("SKU");
  });
});

describe("recommendationsToCsv", () => {
  it("formats recommendations into actionable purchase order & liquidation columns", () => {
    const csvPath = path.join(process.cwd(), "src/data/retail_inventory.csv");
    const { rows } = parseInventoryCsv(readFileSync(csvPath, "utf-8"));
    const classified = classifyInventory(rows);
    const kpis = computePortfolioKpis(classified);
    const risk = computeReorderRiskList(classified);
    const recs = computeInventoryRecommendations(classified, kpis, risk);

    const csvOut = recommendationsToCsv(recs.items);
    const reparsed = Papa.parse(csvOut, { header: true, skipEmptyLines: true });

    expect(reparsed.errors).toEqual([]);
    expect(reparsed.data.length).toBe(recs.items.length);
    const first = reparsed.data[0] as Record<string, string>;
    expect(first).toHaveProperty("SKU");
    expect(first).toHaveProperty("Suggested Order Qty");
    expect(first).toHaveProperty("Estimated Cost ($)");
    expect(first).toHaveProperty("Supplier");
    expect(first).toHaveProperty("Recommended Action");
  });
});

describe("supplierPoToCsv", () => {
  it("generates a vendor-ready purchase order CSV filtered specifically to the requested supplier", () => {
    const csvPath = path.join(process.cwd(), "src/data/retail_inventory.csv");
    const { rows } = parseInventoryCsv(readFileSync(csvPath, "utf-8"));
    const classified = classifyInventory(rows);
    const kpis = computePortfolioKpis(classified);
    const risk = computeReorderRiskList(classified);
    const recs = computeInventoryRecommendations(classified, kpis, risk);

    // Pick a supplier with actual replenishment needs from the sample
    const sampleReplenishment = recs.items.find(
      (i) => i.type === "replenishment" && i.actionData.suggestedOrderQty > 0
    );
    expect(sampleReplenishment).toBeDefined();
    const targetSupplier = sampleReplenishment!.supplier;

    const supplierPoCsv = supplierPoToCsv(targetSupplier, recs.items, {
      poNumber: "PO-TEST-001",
      orderDate: "2026-09-28",
    });

    const reparsed = Papa.parse(supplierPoCsv, { header: true, skipEmptyLines: true });
    expect(reparsed.errors).toEqual([]);
    expect(reparsed.data.length).toBeGreaterThan(0);

    for (const row of reparsed.data as Record<string, string>[]) {
      expect(row["PO Number"]).toBe("PO-TEST-001");
      expect(row["Order Date"]).toBe("2026-09-28");
      expect(row["Supplier"]).toBe(targetSupplier);
      expect(Number(row["Order Quantity"])).toBeGreaterThan(0);
      expect(Number(row["Unit Cost ($)"])).toBeGreaterThan(0);
      expect(Number(row["Line Total ($)"])).toBeGreaterThan(0);
    }
  });

  it("handles a supplier with zero replenishment items cleanly without throwing", () => {
    const poCsv = supplierPoToCsv("Nonexistent Vendor", []);
    const reparsed = Papa.parse(poCsv, { header: true, skipEmptyLines: true });
    expect(reparsed.errors).toEqual([]);
    expect(reparsed.data.length).toBe(0);
  });
});


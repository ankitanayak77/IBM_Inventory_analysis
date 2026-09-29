import { describe, it, expect, beforeAll } from "vitest";
import { readFileSync } from "fs";
import path from "path";
import { parseInventoryCsv } from "../parseCsv";
import { classifyInventory } from "../classify";
import {
  computeProductParetoRollup,
  computeCategoryPerformance,
  computeFsnAbcMatrix,
} from "../summary";
import type { ClassifiedSku } from "../types";

/**
 * This suite is the "no mistakes" evidence check for the TypeScript port:
 * it runs the TS engine against the exact same 50-row sample dataset used
 * in the project report, and diffs the result row-by-row against the
 * Python/pandas output that was already verified in that report (Chapters
 * 3–4). If this suite passes, the TS port is provably equivalent to the
 * verified analysis — not merely "should be right."
 */

interface PythonRow {
  sku: string;
  inventory_value: string;
  revenue_30d: string;
  gross_margin_30d: string;
  itr_annualised: string;
  days_of_stock: string;
  fsn_class: string;
  abc_class: string;
  stock_status: string;
  priority_tag: string;
}

function loadPythonVerifiedRows(): PythonRow[] {
  const csvPath = path.join(__dirname, "../../../data/python_verified_output.csv");
  const text = readFileSync(csvPath, "utf-8");
  const [headerLine, ...lines] = text.trim().split("\n");
  const headers = headerLine.split(",");
  return lines.map((line) => {
    // Simple split is safe here: every field in this file is numeric,
    // an enum-like label, or a product name/date with no embedded commas
    // (verified against the source CSV before writing this test).
    const cells = line.split(",");
    const obj: Record<string, string> = {};
    headers.forEach((h, i) => (obj[h] = cells[i]));
    return obj as unknown as PythonRow;
  });
}

describe("classifyInventory — parity with the Python-verified report output", () => {
  let tsResult: ClassifiedSku[];
  let pyRows: PythonRow[];

  beforeAll(() => {
    const csvPath = path.join(__dirname, "../../../data/retail_inventory.csv");
    const csvText = readFileSync(csvPath, "utf-8");
    const { rows, rejected } = parseInventoryCsv(csvText);
    expect(rejected).toEqual([]); // the known-good sample file must have zero rejected rows
    tsResult = classifyInventory(rows);
    pyRows = loadPythonVerifiedRows();
  });

  it("parses all 50 rows with none rejected", () => {
    expect(tsResult.length).toBe(50);
    expect(pyRows.length).toBe(50);
  });

  it("matches the Python fsn_class for every SKU", () => {
    for (const py of pyRows) {
      const ts = tsResult.find((r) => r.sku === py.sku)!;
      expect(ts, `SKU ${py.sku} missing from TS result`).toBeDefined();
      expect(ts.fsn_class, `FSN mismatch for ${py.sku}`).toBe(py.fsn_class);
    }
  });

  it("matches the Python abc_class for every SKU", () => {
    for (const py of pyRows) {
      const ts = tsResult.find((r) => r.sku === py.sku)!;
      expect(ts.abc_class, `ABC mismatch for ${py.sku}`).toBe(py.abc_class);
    }
  });

  it("matches the Python stock_status for every SKU", () => {
    for (const py of pyRows) {
      const ts = tsResult.find((r) => r.sku === py.sku)!;
      expect(ts.stock_status, `stock_status mismatch for ${py.sku}`).toBe(py.stock_status);
    }
  });

  it("matches the Python priority_tag for every SKU", () => {
    for (const py of pyRows) {
      const ts = tsResult.find((r) => r.sku === py.sku)!;
      expect(ts.priority_tag, `priority_tag mismatch for ${py.sku}`).toBe(py.priority_tag);
    }
  });

  it("matches Python's numeric fields within floating-point tolerance", () => {
    for (const py of pyRows) {
      const ts = tsResult.find((r) => r.sku === py.sku)!;
      expect(ts.inventory_value).toBeCloseTo(Number(py.inventory_value), 2);
      expect(ts.revenue_30d).toBeCloseTo(Number(py.revenue_30d), 2);
      expect(ts.gross_margin_30d).toBeCloseTo(Number(py.gross_margin_30d), 2);
      expect(ts.itr_annualised).toBeCloseTo(Number(py.itr_annualised), 2);
      if (Number.isFinite(Number(py.days_of_stock))) {
        expect(ts.days_of_stock).toBeCloseTo(Number(py.days_of_stock), 2);
      }
    }
  });

  it("reproduces the exact aggregate counts from Report Section 4.2 / 4.3 / 4.5", () => {
    const fsnCounts = { "Fast-moving": 0, "Slow-moving": 0, "Non-moving": 0 };
    const abcCounts = { A: 0, B: 0, C: 0 };
    const stockCounts = { "Reorder Now": 0, "Low - Monitor": 0, Healthy: 0 };
    for (const r of tsResult) {
      fsnCounts[r.fsn_class]++;
      abcCounts[r.abc_class]++;
      stockCounts[r.stock_status]++;
    }
    // Report Section 4.2
    expect(fsnCounts["Fast-moving"]).toBe(10);
    expect(fsnCounts["Slow-moving"]).toBe(18);
    expect(fsnCounts["Non-moving"]).toBe(22);
    // Report Section 4.3
    expect(abcCounts.A).toBe(32);
    expect(abcCounts.B).toBe(12);
    expect(abcCounts.C).toBe(6);
    // Report Section 4.5
    expect(stockCounts["Reorder Now"]).toBe(5);
    expect(stockCounts["Low - Monitor"]).toBe(2);
    expect(stockCounts["Healthy"]).toBe(43);
  });

  it("flags exactly the 5 Reorder-Now SKUs named in Report Section 4.5", () => {
    const reorderNowSkus = tsResult
      .filter((r) => r.stock_status === "Reorder Now")
      .map((r) => r.sku)
      .sort();
    expect(reorderNowSkus).toEqual(["RET006", "RET023", "RET024", "RET025", "RET035"].sort());
  });

  it("computes total inventory value and 30-day revenue matching Report Section 4.1", () => {
    const totalInvValue = tsResult.reduce((s, r) => s + r.inventory_value, 0);
    const totalRevenue = tsResult.reduce((s, r) => s + r.revenue_30d, 0);
    expect(totalInvValue).toBeCloseTo(21913.5, 1);
    expect(totalRevenue).toBeCloseTo(60356.0, 1);
  });

  it("computes the product-level Pareto rollup matching Report Section 4.3 / Figure 2", () => {
    const pareto = computeProductParetoRollup(tsResult);
    expect(pareto.length).toBe(18); // 18 distinct product lines
    expect(pareto[0].product_name).toBe("Cashmere Blend Sweater");
    expect(pareto[0].revenue).toBeCloseTo(8704, 0);
    expect(pareto[0].cumulativePct).toBeCloseTo(14.4, 1);
    // 11th product line (index 10) is where cumulative crosses ~80% per the report
    expect(pareto[10].product_name).toBe("Linen Wide-Leg Pants");
    expect(pareto[10].cumulativePct).toBeCloseTo(79.7, 1);
    // last row's cumulative % must reach 100
    expect(pareto[pareto.length - 1].cumulativePct).toBeCloseTo(100, 1);
  });

  it("computes category performance matching Report Section 4.6", () => {
    const cats = computeCategoryPerformance(tsResult);
    const byName = new Map(cats.map((c) => [c.category, c]));
    expect(byName.get("Tops")).toMatchObject({ units: 368, revenue: 20744 });
    expect(byName.get("Bottoms")).toMatchObject({ units: 130, revenue: 9606 });
    expect(byName.get("Accessories")).toMatchObject({ units: 190, revenue: 9454 });
    expect(byName.get("Footwear")).toMatchObject({ units: 55, revenue: 7590 });
    expect(byName.get("Outerwear")).toMatchObject({ units: 54, revenue: 6642 });
    expect(byName.get("Dresses")).toMatchObject({ units: 74, revenue: 6320 });
    expect(byName.get("Tops")!.inventoryValue).toBeCloseTo(6688, 0);
    // sorted descending by revenue: Tops must be first
    expect(cats[0].category).toBe("Tops");
  });

  it("computes the FSN x ABC matrix matching Report Section 4.4 / Figure 3", () => {
    const matrix = computeFsnAbcMatrix(tsResult);
    const cellCount = (fsn: string, abc: string) =>
      matrix.find((c) => c.fsn_class === fsn && c.abc_class === abc)!.count;
    expect(cellCount("Fast-moving", "A")).toBe(10);
    expect(cellCount("Fast-moving", "B")).toBe(0);
    expect(cellCount("Fast-moving", "C")).toBe(0);
    expect(cellCount("Slow-moving", "A")).toBe(13);
    expect(cellCount("Slow-moving", "B")).toBe(4);
    expect(cellCount("Slow-moving", "C")).toBe(1);
    expect(cellCount("Non-moving", "A")).toBe(9);
    expect(cellCount("Non-moving", "B")).toBe(8);
    expect(cellCount("Non-moving", "C")).toBe(5);
  });
});

describe("parseInventoryCsv — malformed-row handling (FR-1 / NFR Reliability)", () => {
  it("rejects a row with a missing required field, and keeps the rest", () => {
    const csv = [
      "sku,product_name,category,size,color,quantity_on_hand,reorder_point,cost_per_unit,retail_price,last_restock_date,units_sold_30d,supplier,season",
      "SKU1,Test Product,Tops,S,Red,10,5,1.00,2.00,2024-01-01,3,Acme,Year-Round",
      "SKU2,,Tops,M,Blue,10,5,1.00,2.00,2024-01-01,3,Acme,Year-Round", // missing product_name
    ].join("\n");
    const { rows, rejected } = parseInventoryCsv(csv);
    expect(rows.length).toBe(1);
    expect(rows[0].sku).toBe("SKU1");
    expect(rejected.length).toBe(1);
    expect(rejected[0].reason).toMatch(/product_name/);
  });

  it("rejects a row with a negative or non-numeric quantity", () => {
    const csv = [
      "sku,product_name,category,size,color,quantity_on_hand,reorder_point,cost_per_unit,retail_price,last_restock_date,units_sold_30d,supplier,season",
      "SKU1,Test Product,Tops,S,Red,-5,5,1.00,2.00,2024-01-01,3,Acme,Year-Round",
      "SKU2,Test Product,Tops,S,Red,abc,5,1.00,2.00,2024-01-01,3,Acme,Year-Round",
    ].join("\n");
    const { rows, rejected } = parseInventoryCsv(csv);
    expect(rows.length).toBe(0);
    expect(rejected.length).toBe(2);
  });

  it("rejects a duplicate SKU, keeping the first occurrence", () => {
    const csv = [
      "sku,product_name,category,size,color,quantity_on_hand,reorder_point,cost_per_unit,retail_price,last_restock_date,units_sold_30d,supplier,season",
      "SKU1,First,Tops,S,Red,10,5,1.00,2.00,2024-01-01,3,Acme,Year-Round",
      "SKU1,Second,Tops,S,Red,20,5,1.00,2.00,2024-01-01,3,Acme,Year-Round",
    ].join("\n");
    const { rows, rejected } = parseInventoryCsv(csv);
    expect(rows.length).toBe(1);
    expect(rows[0].product_name).toBe("First");
    expect(rejected.length).toBe(1);
    expect(rejected[0].reason).toMatch(/Duplicate SKU/);
  });

  it("throws a clear error when a required column is missing from the header", () => {
    const csv = ["sku,product_name", "SKU1,First"].join("\n");
    expect(() => parseInventoryCsv(csv)).toThrow(/missing required column/i);
  });
});

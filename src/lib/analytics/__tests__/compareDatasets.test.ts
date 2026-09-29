import { describe, it, expect } from "vitest";
import { findNewlyAtRisk } from "../compareDatasets";
import type { ClassifiedSku } from "../types";

function sku(overrides: Partial<ClassifiedSku> & { sku: string; stock_status: ClassifiedSku["stock_status"] }): ClassifiedSku {
  return {
    product_name: "Test Product",
    category: "Tops",
    size: "M",
    color: "Red",
    quantity_on_hand: 5,
    reorder_point: 10,
    cost_per_unit: 10,
    retail_price: 20,
    last_restock_date: "2024-01-01",
    units_sold_30d: 5,
    supplier: "Acme",
    season: "Year-Round",
    inventory_value: 50,
    revenue_30d: 100,
    gross_margin_30d: 50,
    itr_annualised: 12,
    days_of_stock: 5,
    fsn_class: "Fast-moving",
    abc_class: "A",
    abc_revenue_share: 0.1,
    abc_cumulative_share: 0.1,
    priority_tag: "Critical - protect availability",
    ...overrides,
  };
}

describe("findNewlyAtRisk — Report FR-10 comparison logic", () => {
  it("with no previous dataset, every currently 'Reorder Now' SKU counts as newly at risk", () => {
    const current = [
      sku({ sku: "A", stock_status: "Reorder Now" }),
      sku({ sku: "B", stock_status: "Healthy" }),
      sku({ sku: "C", stock_status: "Reorder Now" }),
    ];
    const result = findNewlyAtRisk(null, current);
    expect(result.map((r) => r.sku).sort()).toEqual(["A", "C"]);
  });

  it("excludes a SKU that was already 'Reorder Now' in the previous dataset", () => {
    const previous = [sku({ sku: "A", stock_status: "Reorder Now" })];
    const current = [sku({ sku: "A", stock_status: "Reorder Now" })];
    expect(findNewlyAtRisk(previous, current)).toEqual([]);
  });

  it("includes a SKU that was 'Healthy' before and is 'Reorder Now' now", () => {
    const previous = [sku({ sku: "A", stock_status: "Healthy" })];
    const current = [sku({ sku: "A", stock_status: "Reorder Now" })];
    const result = findNewlyAtRisk(previous, current);
    expect(result.map((r) => r.sku)).toEqual(["A"]);
  });

  it("includes a SKU that was 'Low - Monitor' before and is 'Reorder Now' now", () => {
    const previous = [sku({ sku: "A", stock_status: "Low - Monitor" })];
    const current = [sku({ sku: "A", stock_status: "Reorder Now" })];
    expect(findNewlyAtRisk(previous, current).map((r) => r.sku)).toEqual(["A"]);
  });

  it("includes a SKU that is 'Reorder Now' now but didn't exist in the previous dataset at all", () => {
    const previous = [sku({ sku: "B", stock_status: "Healthy" })];
    const current = [sku({ sku: "A", stock_status: "Reorder Now" }), sku({ sku: "B", stock_status: "Healthy" })];
    expect(findNewlyAtRisk(previous, current).map((r) => r.sku)).toEqual(["A"]);
  });

  it("never includes a SKU that is 'Healthy' now, regardless of its previous status", () => {
    const previous = [sku({ sku: "A", stock_status: "Reorder Now" })];
    const current = [sku({ sku: "A", stock_status: "Healthy" })];
    expect(findNewlyAtRisk(previous, current)).toEqual([]);
  });

  it("excludes a SKU that was 'Reorder Now' previously but is absent from the current dataset", () => {
    const previous = [sku({ sku: "A", stock_status: "Reorder Now" })];
    const current: ClassifiedSku[] = [];
    expect(findNewlyAtRisk(previous, current)).toEqual([]);
  });

  it("handles both empty previous and current without throwing", () => {
    expect(findNewlyAtRisk([], [])).toEqual([]);
    expect(findNewlyAtRisk(null, [])).toEqual([]);
  });
});

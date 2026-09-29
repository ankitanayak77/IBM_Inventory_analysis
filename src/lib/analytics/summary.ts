import type { ClassifiedSku, FsnClass, AbcClass, StockStatus } from "./types";

export interface PortfolioKpis {
  totalSkus: number;
  distinctProducts: number;
  totalInventoryValue: number;
  totalRevenue30d: number;
  totalGrossMargin30d: number;
  grossMarginPct: number;
  gmroi: number; // Annualized Gross Margin Return on Investment (APICS standard)
  medianItr: number;
  minItr: number;
  maxItr: number;
  atRiskSkuCount: number; // Reorder Now + Low - Monitor
}

export interface FsnBreakdownRow {
  fsn_class: FsnClass;
  skuCount: number;
  pctOfSkus: number;
  inventoryValue: number;
  pctOfValue: number;
}

export interface AbcBreakdownRow {
  abc_class: AbcClass;
  skuCount: number;
  pctOfSkus: number;
  revenue: number;
  pctOfRevenue: number;
}

function median(nums: number[]): number {
  const sorted = [...nums].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 !== 0 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

/** Report Section 4.1 — Portfolio Overview */
export function computePortfolioKpis(rows: ClassifiedSku[]): PortfolioKpis {
  const totalInventoryValue = rows.reduce((s, r) => s + r.inventory_value, 0);
  const totalRevenue30d = rows.reduce((s, r) => s + r.revenue_30d, 0);
  const totalGrossMargin30d = rows.reduce((s, r) => s + r.gross_margin_30d, 0);
  const itrValues = rows.map((r) => r.itr_annualised);
  const atRiskSkuCount = rows.filter(
    (r) => r.stock_status === "Reorder Now" || r.stock_status === "Low - Monitor"
  ).length;

  const gmroi = totalInventoryValue > 0 ? (totalGrossMargin30d * 12) / totalInventoryValue : 0;

  return {
    totalSkus: rows.length,
    distinctProducts: new Set(rows.map((r) => r.product_name)).size,
    totalInventoryValue,
    totalRevenue30d,
    totalGrossMargin30d,
    grossMarginPct: totalRevenue30d > 0 ? (totalGrossMargin30d / totalRevenue30d) * 100 : 0,
    gmroi,
    medianItr: median(itrValues),
    minItr: Math.min(...itrValues),
    maxItr: Math.max(...itrValues),
    atRiskSkuCount,
  };
}

/** Report Section 4.2 — FSN distribution table */
export function computeFsnBreakdown(rows: ClassifiedSku[]): FsnBreakdownRow[] {
  const order: FsnClass[] = ["Fast-moving", "Slow-moving", "Non-moving"];
  const totalValue = rows.reduce((s, r) => s + r.inventory_value, 0);
  return order.map((cls) => {
    const subset = rows.filter((r) => r.fsn_class === cls);
    const inventoryValue = subset.reduce((s, r) => s + r.inventory_value, 0);
    return {
      fsn_class: cls,
      skuCount: subset.length,
      pctOfSkus: (subset.length / rows.length) * 100,
      inventoryValue,
      pctOfValue: totalValue > 0 ? (inventoryValue / totalValue) * 100 : 0,
    };
  });
}

/** Report Section 4.3 — ABC distribution table */
export function computeAbcBreakdown(rows: ClassifiedSku[]): AbcBreakdownRow[] {
  const order: AbcClass[] = ["A", "B", "C"];
  const totalRevenue = rows.reduce((s, r) => s + r.revenue_30d, 0);
  return order.map((cls) => {
    const subset = rows.filter((r) => r.abc_class === cls);
    const revenue = subset.reduce((s, r) => s + r.revenue_30d, 0);
    return {
      abc_class: cls,
      skuCount: subset.length,
      pctOfSkus: (subset.length / rows.length) * 100,
      revenue,
      pctOfRevenue: totalRevenue > 0 ? (revenue / totalRevenue) * 100 : 0,
    };
  });
}

/** Report Section 4.5 — reorder-risk list, sorted by urgency (fewest days first) */
export function computeReorderRiskList(rows: ClassifiedSku[]): ClassifiedSku[] {
  const statusRank: Record<StockStatus, number> = { "Reorder Now": 0, "Low - Monitor": 1, Healthy: 2 };
  return rows
    .filter((r) => r.stock_status !== "Healthy")
    .sort((a, b) => statusRank[a.stock_status] - statusRank[b.stock_status] || a.days_of_stock - b.days_of_stock);
}

export interface ProductParetoRow {
  product_name: string;
  revenue: number;
  units: number;
  pctOfRevenue: number;
  cumulativePct: number;
}

/** Report Section 4.3 / Figure 2 — product-line rollup with cumulative % of revenue */
export function computeProductParetoRollup(rows: ClassifiedSku[]): ProductParetoRow[] {
  const byProduct = new Map<string, { revenue: number; units: number }>();
  for (const r of rows) {
    const cur = byProduct.get(r.product_name) ?? { revenue: 0, units: 0 };
    cur.revenue += r.revenue_30d;
    cur.units += r.units_sold_30d;
    byProduct.set(r.product_name, cur);
  }
  const totalRevenue = rows.reduce((s, r) => s + r.revenue_30d, 0);

  // Stable sort descending by revenue (ties keep Map insertion order, i.e. CSV order).
  const sorted = [...byProduct.entries()].sort((a, b) => b[1].revenue - a[1].revenue);

  let cumulative = 0;
  return sorted.map(([product_name, { revenue, units }]) => {
    const pctOfRevenue = totalRevenue > 0 ? (revenue / totalRevenue) * 100 : 0;
    cumulative += pctOfRevenue;
    return { product_name, revenue, units, pctOfRevenue, cumulativePct: cumulative };
  });
}

export interface CategoryPerformanceRow {
  category: string;
  units: number;
  revenue: number;
  inventoryValue: number;
  grossMargin: number;
  grossMarginPct: number;
  gmroi: number; // Annualized Gross Margin Return on Investment
  skuCount: number;
  pctOfRevenue: number;
  pctOfInventoryValue: number;
}

/** Report Section 4.6 / Figure 5 — category rollup, sorted by revenue descending */
export function computeCategoryPerformance(rows: ClassifiedSku[]): CategoryPerformanceRow[] {
  const byCategory = new Map<
    string,
    {
      category: string;
      units: number;
      revenue: number;
      inventoryValue: number;
      grossMargin: number;
      skuCount: number;
    }
  >();

  for (const r of rows) {
    const cur = byCategory.get(r.category) ?? {
      category: r.category,
      units: 0,
      revenue: 0,
      inventoryValue: 0,
      grossMargin: 0,
      skuCount: 0,
    };
    cur.units += r.units_sold_30d;
    cur.revenue += r.revenue_30d;
    cur.inventoryValue += r.inventory_value;
    cur.grossMargin += r.gross_margin_30d;
    cur.skuCount += 1;
    byCategory.set(r.category, cur);
  }

  const totalRevenue = rows.reduce((s, r) => s + r.revenue_30d, 0);
  const totalValue = rows.reduce((s, r) => s + r.inventory_value, 0);

  return [...byCategory.values()]
    .sort((a, b) => b.revenue - a.revenue)
    .map((c) => ({
      category: c.category,
      units: c.units,
      revenue: c.revenue,
      inventoryValue: c.inventoryValue,
      grossMargin: c.grossMargin,
      grossMarginPct: c.revenue > 0 ? (c.grossMargin / c.revenue) * 100 : 0,
      gmroi: c.inventoryValue > 0 ? (c.grossMargin * 12) / c.inventoryValue : 0,
      skuCount: c.skuCount,
      pctOfRevenue: totalRevenue > 0 ? (c.revenue / totalRevenue) * 100 : 0,
      pctOfInventoryValue: totalValue > 0 ? (c.inventoryValue / totalValue) * 100 : 0,
    }));
}

export interface FsnAbcMatrixCell {
  fsn_class: FsnClass;
  abc_class: AbcClass;
  count: number;
}

/** Report Section 4.4 / Figure 3 — FSN x ABC cross-tab, fixed row/column order */
export function computeFsnAbcMatrix(rows: ClassifiedSku[]): FsnAbcMatrixCell[] {
  const fsnOrder: FsnClass[] = ["Fast-moving", "Slow-moving", "Non-moving"];
  const abcOrder: AbcClass[] = ["A", "B", "C"];
  const cells: FsnAbcMatrixCell[] = [];
  for (const fsn_class of fsnOrder) {
    for (const abc_class of abcOrder) {
      const count = rows.filter((r) => r.fsn_class === fsn_class && r.abc_class === abc_class).length;
      cells.push({ fsn_class, abc_class, count });
    }
  }
  return cells;
}

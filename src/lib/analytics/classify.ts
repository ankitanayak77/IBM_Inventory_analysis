import type {
  RawSkuRow,
  ClassifiedSku,
  FsnClass,
  AbcClass,
  StockStatus,
  PriorityTag,
} from "./types";

/**
 * Inventory Analysis engine — TypeScript port of the Python/pandas pipeline
 * verified in the project report (Chapters 3–4). Every formula and threshold
 * below is cited in the report:
 *  - FSN via SKU-share ranking (Report Section 3.2, point 2)
 *  - ABC via cumulative revenue share (Report Section 2.2 / 4.3)
 *  - Reorder status thresholds (Report Section 3.3)
 *  - Priority tag rules (Report Section 4.4)
 *
 * This module is intentionally pure (no I/O) so it is trivially unit-testable
 * and reusable from both a CLI script and a Next.js API route.
 */

// ---------------------------------------------------------------------------
// Step 1 — per-row derived metrics (Report Section 3.3)
// ---------------------------------------------------------------------------
interface WithDerivedMetrics extends RawSkuRow {
  inventory_value: number;
  revenue_30d: number;
  gross_margin_30d: number;
  itr_annualised: number;
  days_of_stock: number;
}

function withDerivedMetrics(row: RawSkuRow): WithDerivedMetrics {
  const inventory_value = row.quantity_on_hand * row.cost_per_unit;
  const revenue_30d = row.units_sold_30d * row.retail_price;
  const gross_margin_30d =
    row.units_sold_30d * (row.retail_price - row.cost_per_unit);

  // Annualised Inventory Turnover Ratio — proxy per Report Section 3.2, point 1:
  // (30-day units sold × 12) ÷ current on-hand quantity.
  //
  // Edge case discovered via the 10,000-SKU load test (not present in the
  // 50-row sample, which never has quantity_on_hand = 0): a stocked-out SKU
  // makes this a division by zero. units_sold_30d/0 with sold>0 is +Infinity
  // in JS (not an error) and is semantically correct here — a SKU that sold
  // units while completely out of stock is the most extreme "fast" signal
  // possible, and Infinity sorts to the top of the FSN ranking as intended.
  // But 0/0 is NaN, which is NOT semantically meaningful (no stock and no
  // recorded sales gives no evidence of velocity either way) and, left as
  // NaN, corrupts Array.sort's ordering for every row it's compared against
  // — confirmed empirically: it misclassified a zero-velocity SKU as
  // "Fast-moving". Defined as 0 instead: the conservative, sortable choice,
  // which correctly lands these SKUs in the slowest (Non-moving) tier.
  const itr_annualised =
    row.quantity_on_hand > 0
      ? (row.units_sold_30d * 12) / row.quantity_on_hand
      : row.units_sold_30d > 0
        ? Infinity
        : 0;

  // Days of stock remaining at the current 30-day sales run-rate.
  // Same load-test-discovered edge case: a SKU with zero stock and zero
  // recorded sales must show 0 days remaining (it is already out), not
  // Infinity — Infinity should mean "never sells, so never runs out",
  // which only applies when there IS stock on hand.
  const dailyRate = row.units_sold_30d / 30;
  const days_of_stock =
    row.quantity_on_hand === 0 ? 0 : dailyRate > 0 ? row.quantity_on_hand / dailyRate : Infinity;

  return { ...row, inventory_value, revenue_30d, gross_margin_30d, itr_annualised, days_of_stock };
}

// ---------------------------------------------------------------------------
// Step 2 — FSN classification (relative SKU-share ranking)
// ---------------------------------------------------------------------------
// Report Section 3.2, point 2: absolute ITR>3 cut-offs return 50/0/0 on this
// catalog, so we rank all SKUs by ITR (stable sort — ties keep their original
// CSV order, matching pandas' rank(method="first")) and apply the published
// SKU-share bands: top 20% Fast, next 35% Slow, remaining 45% Non-moving.
function assignFsnClasses<T extends WithDerivedMetrics>(rows: T[]): (T & { fsn_class: FsnClass })[] {
  const n = rows.length;
  const fastCut = Math.round(0.2 * n);
  const slowCut = Math.round(0.55 * n);

  // Stable sort descending by ITR — Array.prototype.sort is guaranteed stable
  // in Node.js / V8 (ECMA-262 since ES2019), so ties preserve input order.
  const byItrDesc = [...rows].sort((a, b) => b.itr_annualised - a.itr_annualised);

  const classOf = new Map<string, FsnClass>();
  byItrDesc.forEach((row, i) => {
    const rank = i + 1; // 1-based rank, matching the Python implementation
    const cls: FsnClass =
      rank <= fastCut ? "Fast-moving" : rank <= slowCut ? "Slow-moving" : "Non-moving";
    classOf.set(row.sku, cls);
  });

  return rows.map((row) => ({ ...row, fsn_class: classOf.get(row.sku)! }));
}

// ---------------------------------------------------------------------------
// Step 3 — ABC classification (cumulative % of 30-day revenue)
// ---------------------------------------------------------------------------
// Report Section 2.2 / 4.3: cumulative-revenue-share cut-offs of 80% / 95% / 100%.
function assignAbcClasses<T extends WithDerivedMetrics>(
  rows: T[]
): (T & { abc_class: AbcClass; abc_revenue_share: number; abc_cumulative_share: number })[] {
  const totalRevenue = rows.reduce((sum, r) => sum + r.revenue_30d, 0);

  const byRevenueDesc = [...rows].sort((a, b) => b.revenue_30d - a.revenue_30d);

  const infoOf = new Map<string, { cls: AbcClass; share: number; cumShare: number }>();
  let cumulative = 0;
  for (const row of byRevenueDesc) {
    const share = totalRevenue > 0 ? row.revenue_30d / totalRevenue : 0;
    cumulative += share;
    const cls: AbcClass = cumulative <= 0.8 ? "A" : cumulative <= 0.95 ? "B" : "C";
    infoOf.set(row.sku, { cls, share, cumShare: cumulative });
  }

  return rows.map((row) => {
    const info = infoOf.get(row.sku)!;
    return { ...row, abc_class: info.cls, abc_revenue_share: info.share, abc_cumulative_share: info.cumShare };
  });
}

// ---------------------------------------------------------------------------
// Step 4 — stock status (Report Section 3.3)
// ---------------------------------------------------------------------------
function stockStatusOf(row: WithDerivedMetrics): StockStatus {
  if (row.quantity_on_hand <= row.reorder_point) return "Reorder Now";
  if (row.quantity_on_hand <= 1.25 * row.reorder_point) return "Low - Monitor";
  return "Healthy";
}

// ---------------------------------------------------------------------------
// Step 5 — combined FSN × ABC priority tag (Report Section 4.4)
// ---------------------------------------------------------------------------
function priorityTagOf(fsn: FsnClass, abc: AbcClass): PriorityTag {
  if (abc === "A" && fsn === "Fast-moving") return "Critical - protect availability";
  if (abc === "A" && (fsn === "Slow-moving" || fsn === "Non-moving"))
    return "High-value at risk - investigate";
  if (fsn === "Non-moving" && abc === "C") return "Discontinue candidate";
  if (fsn === "Fast-moving" && (abc === "B" || abc === "C")) return "Undervalued fast mover";
  return "Routine review";
}

// ---------------------------------------------------------------------------
// Public entry point
// ---------------------------------------------------------------------------
export function classifyInventory(rawRows: RawSkuRow[]): ClassifiedSku[] {
  const withMetrics = rawRows.map(withDerivedMetrics);
  const withFsn = assignFsnClasses(withMetrics);
  const withAbc = assignAbcClasses(withFsn);

  return withAbc.map((row) => ({
    ...row,
    stock_status: stockStatusOf(row),
    priority_tag: priorityTagOf(row.fsn_class, row.abc_class),
    abc_cumulative_share: row.abc_cumulative_share, // keep explicit for clarity
  }));
}

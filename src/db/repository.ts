import { eq, desc, sql } from "drizzle-orm";
import { getDb } from "./client";
import { datasets, skuRecords } from "./schema";
import { parseNumericString } from "./dbSerialization";
import type { ClassifiedSku } from "@/lib/analytics/types";
import { analyzeCsvText } from "@/lib/analytics/analyze";
import type { AnalysisResult } from "@/lib/analytics/analyze";
import {
  computePortfolioKpis,
  computeFsnBreakdown,
  computeAbcBreakdown,
  computeReorderRiskList,
  computeProductParetoRollup,
  computeCategoryPerformance,
  computeFsnAbcMatrix,
} from "@/lib/analytics/summary";
import { computeInventoryRecommendations } from "@/lib/analytics/recommendations";

/**
 * Persistence for Phase 2. Deliberately stores only the classified,
 * SKU-level facts (one row per SKU per dataset) and *recomputes* every
 * aggregation (KPIs, FSN/ABC breakdowns, Pareto, etc.) from those facts on
 * read, using the exact same pure functions the live CSV-upload path
 * uses (src/lib/analytics/summary.ts) — the same single-source-of-truth
 * principle as analyzeCsvText (Step 3): there is no second, separately
 * stored copy of the aggregates that could silently drift from what the
 * verified classification logic actually produces.
 */

export interface DatasetSummary {
  id: number;
  sourceLabel: string;
  uploadedAt: Date;
  skuCount: number;
  rejectedRowCount: number;
}

/** Persists a fully-classified AnalysisResult as a new dataset. Returns the new dataset's id. */
export async function saveAnalysisResult(result: AnalysisResult, sourceLabel: string): Promise<{ datasetId: number }> {
  const db = getDb();

  return db.transaction(async (tx) => {
    const [{ id: datasetId }] = await tx
      .insert(datasets)
      .values({
        sourceLabel,
        skuCount: result.rows.length,
        rejectedRowCount: result.rejected.length,
      })
      .returning({ id: datasets.id });

    if (result.rows.length > 0) {
      const values = result.rows.map((row) => ({
        datasetId,
        sku: row.sku,
        productName: row.product_name,
        category: row.category,
        size: row.size,
        color: row.color,
        quantityOnHand: row.quantity_on_hand,
        reorderPoint: row.reorder_point,
        costPerUnit: row.cost_per_unit,
        retailPrice: row.retail_price,
        lastRestockDate: row.last_restock_date,
        unitsSold30d: row.units_sold_30d,
        supplier: row.supplier,
        season: row.season,
        inventoryValue: row.inventory_value,
        revenue30d: row.revenue_30d,
        grossMargin30d: row.gross_margin_30d,
        itrAnnualised: String(row.itr_annualised), // string mode — see schema.ts
        daysOfStock: String(row.days_of_stock), // string mode — see schema.ts
        fsnClass: row.fsn_class,
        abcClass: row.abc_class,
        abcRevenueShare: row.abc_revenue_share,
        abcCumulativeShare: row.abc_cumulative_share,
        stockStatus: row.stock_status,
        priorityTag: row.priority_tag,
      }));

      // Batched, not one INSERT for all rows — confirmed by direct testing
      // (10,000-row synthetic catalog, Step 4's fixture) that a single
      // multi-row insert() call throws "Maximum call stack size exceeded"
      // inside Drizzle's own SQL-fragment builder well before Postgres's
      // separate, harder 65,535-parameter-per-statement protocol limit
      // is even reached (sku_records has 26 columns, so 65535/26 ≈ 2520
      // rows would be Postgres's own ceiling). 500 rows/batch (13,000
      // params) stays safely under both.
      const BATCH_SIZE = 500;
      for (let i = 0; i < values.length; i += BATCH_SIZE) {
        await tx.insert(skuRecords).values(values.slice(i, i + BATCH_SIZE));
      }
    }

    return { datasetId };
  });
}

/** Lists all persisted datasets, most recent first. */
export async function listDatasets(): Promise<DatasetSummary[]> {
  const db = getDb();
  const rows = await db.select().from(datasets).orderBy(desc(datasets.uploadedAt));
  return rows.map((r) => ({
    id: r.id,
    sourceLabel: r.sourceLabel,
    uploadedAt: r.uploadedAt,
    skuCount: r.skuCount,
    rejectedRowCount: r.rejectedRowCount,
  }));
}

/** Maps one raw sku_records DB row into the ClassifiedSku shape (shared by every function that reads this table). */
function mapDbRowToClassifiedSku(r: typeof skuRecords.$inferSelect): ClassifiedSku {
  return {
    sku: r.sku,
    product_name: r.productName,
    category: r.category,
    size: r.size,
    color: r.color,
    quantity_on_hand: r.quantityOnHand,
    reorder_point: r.reorderPoint,
    cost_per_unit: r.costPerUnit,
    retail_price: r.retailPrice,
    last_restock_date: r.lastRestockDate,
    units_sold_30d: r.unitsSold30d,
    supplier: r.supplier,
    season: r.season,
    inventory_value: r.inventoryValue,
    revenue_30d: r.revenue30d,
    gross_margin_30d: r.grossMargin30d,
    itr_annualised: parseNumericString(r.itrAnnualised),
    days_of_stock: parseNumericString(r.daysOfStock),
    fsn_class: r.fsnClass as ClassifiedSku["fsn_class"],
    abc_class: r.abcClass as ClassifiedSku["abc_class"],
    abc_revenue_share: r.abcRevenueShare,
    abc_cumulative_share: r.abcCumulativeShare,
    stock_status: r.stockStatus as ClassifiedSku["stock_status"],
    priority_tag: r.priorityTag as ClassifiedSku["priority_tag"],
  };
}

/** Reconstructs the classified rows for one dataset from storage (shared by loadDataset and getPreviousDatasetRows). */
async function loadDatasetRows(datasetId: number): Promise<ClassifiedSku[]> {
  const db = getDb();
  const storedRows = await db.select().from(skuRecords).where(eq(skuRecords.datasetId, datasetId));
  return storedRows.map(mapDbRowToClassifiedSku);
}

/** Loads one dataset's full AnalysisResult back, or null if it doesn't exist. */
export async function loadDataset(datasetId: number): Promise<(AnalysisResult & { sourceLabel: string }) | null> {
  const db = getDb();

  const [datasetRow] = await db.select().from(datasets).where(eq(datasets.id, datasetId));
  if (!datasetRow) return null;

  const rows = await loadDatasetRows(datasetId);
  const kpis = computePortfolioKpis(rows);
  const reorderRisk = computeReorderRiskList(rows);

  return {
    sourceLabel: datasetRow.sourceLabel,
    rows,
    rejected: [], // not persisted (Report FR-1 rejects are surfaced at upload time, not stored)
    kpis,
    fsn: computeFsnBreakdown(rows),
    abc: computeAbcBreakdown(rows),
    reorderRisk,
    pareto: computeProductParetoRollup(rows),
    categoryPerf: computeCategoryPerformance(rows),
    matrix: computeFsnAbcMatrix(rows),
    recommendations: computeInventoryRecommendations(rows, kpis, reorderRisk),
  };
}

/**
 * Report FR-10 support: the classified rows of the dataset uploaded
 * immediately before `beforeDatasetId` (by uploadedAt), or null if this
 * is the first dataset ever saved. Ordered by id descending as the
 * tie-break for datasets saved in the same instant (uploadedAt has only
 * timestamp — not sub-millisecond — resolution, and two uploads landing
 * in the same millisecond, while unlikely, should still resolve
 * deterministically rather than depend on undefined ORDER BY behavior).
 */
export async function getPreviousDatasetRows(beforeDatasetId: number): Promise<ClassifiedSku[] | null> {
  const db = getDb();
  const [current] = await db.select().from(datasets).where(eq(datasets.id, beforeDatasetId));
  if (!current) return null;

  const [previous] = await db
    .select()
    .from(datasets)
    .where(sql`(${datasets.uploadedAt}, ${datasets.id}) < (${current.uploadedAt}, ${current.id})`)
    .orderBy(desc(datasets.uploadedAt), desc(datasets.id))
    .limit(1);

  if (!previous) return null;
  return loadDatasetRows(previous.id);
}

/** Convenience: classify raw CSV text and persist it in one call. */
export async function analyzeAndSave(csvText: string, sourceLabel: string) {
  const result = analyzeCsvText(csvText);
  const { datasetId } = await saveAnalysisResult(result, sourceLabel);
  return { result, datasetId };
}

export interface SkuHistoryEntry {
  datasetId: number;
  sourceLabel: string;
  uploadedAt: Date;
  record: ClassifiedSku;
}

/**
 * Report Section 7.5 ("SKU Detail... with its full sales history") —
 * built as a genuine time series across every persisted dataset that
 * contains this SKU, ordered oldest first, which the original report
 * scoped only as a single-snapshot view since Phase 2 (real persistence)
 * didn't exist yet when that chapter was written. A plain join + filter,
 * not a special query type — this is the same `sku_records` table every
 * other repository function already reads, just filtered by `sku`
 * instead of `dataset_id`.
 */
export async function getSkuHistory(sku: string): Promise<SkuHistoryEntry[]> {
  const db = getDb();
  const rows = await db
    .select({ record: skuRecords, datasetId: datasets.id, sourceLabel: datasets.sourceLabel, uploadedAt: datasets.uploadedAt })
    .from(skuRecords)
    .innerJoin(datasets, eq(skuRecords.datasetId, datasets.id))
    .where(eq(skuRecords.sku, sku))
    .orderBy(datasets.uploadedAt);

  return rows.map((r) => ({
    datasetId: r.datasetId,
    sourceLabel: r.sourceLabel,
    uploadedAt: r.uploadedAt,
    record: mapDbRowToClassifiedSku(r.record),
  }));
}

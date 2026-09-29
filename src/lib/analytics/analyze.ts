import { parseInventoryCsv, type RejectedRow } from "./parseCsv";
import { classifyInventory } from "./classify";
import type { ClassifiedSku } from "./types";
import {
  computePortfolioKpis,
  computeFsnBreakdown,
  computeAbcBreakdown,
  computeReorderRiskList,
  computeProductParetoRollup,
  computeCategoryPerformance,
  computeFsnAbcMatrix,
  type PortfolioKpis,
  type FsnBreakdownRow,
  type AbcBreakdownRow,
  type ProductParetoRow,
  type CategoryPerformanceRow,
  type FsnAbcMatrixCell,
} from "./summary";
import {
  computeInventoryRecommendations,
  type InventoryRecommendationsSummary,
} from "./recommendations";

/**
 * The single result shape shared by the server-rendered sample page
 * (`src/app/page.tsx`) and the CSV-upload API route (`/api/upload`).
 * Having one function produce this for both call sites means the two
 * ways of getting data into the dashboard can never silently drift from
 * each other's numbers.
 */
export interface AnalysisResult {
  rows: ClassifiedSku[];
  rejected: RejectedRow[];
  kpis: PortfolioKpis;
  fsn: FsnBreakdownRow[];
  abc: AbcBreakdownRow[];
  reorderRisk: ClassifiedSku[];
  pareto: ProductParetoRow[];
  categoryPerf: CategoryPerformanceRow[];
  matrix: FsnAbcMatrixCell[];
  recommendations: InventoryRecommendationsSummary;
}

/**
 * Runs the full report-verified pipeline (Report Chapters 2–4) on raw CSV
 * text: parse + validate (Section 3.1) -> classify (Sections 2–3) ->
 * every aggregation behind Section 4's tables and Figures 1–6 ->
 * strategic inventory recommendations and executive report metrics.
 *
 * Throws only when the CSV header itself is missing a required column
 * (parseInventoryCsv's one throwing case) — anything row-level is
 * collected in `rejected` instead, per the "reject with a reason, never
 * silently drop or corrupt" rule (Report FR-1 / NFR "Reliability").
 */
export function analyzeCsvText(csvText: string): AnalysisResult {
  const { rows: rawRows, rejected } = parseInventoryCsv(csvText);
  const rows = classifyInventory(rawRows);
  const kpis = computePortfolioKpis(rows);
  const reorderRisk = computeReorderRiskList(rows);
  const recommendations = computeInventoryRecommendations(rows, kpis, reorderRisk);

  return {
    rows,
    rejected,
    kpis,
    fsn: computeFsnBreakdown(rows),
    abc: computeAbcBreakdown(rows),
    reorderRisk,
    pareto: computeProductParetoRollup(rows),
    categoryPerf: computeCategoryPerformance(rows),
    matrix: computeFsnAbcMatrix(rows),
    recommendations,
  };
}

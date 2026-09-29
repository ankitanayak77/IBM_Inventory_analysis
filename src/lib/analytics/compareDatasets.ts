import type { ClassifiedSku } from "./types";

/**
 * Report FR-10: "Send an alert (email or in-app) when a SKU newly
 * crosses into 'Reorder Now.'" This is the comparison at the heart of
 * that: given the previous dataset's classified rows (or null if there
 * is no previous dataset yet) and the current ones, which SKUs are
 * "Reorder Now" now but weren't before?
 *
 * Matched by `sku` (not row id, which is new per dataset/upload) — a SKU
 * newly counts as "at risk" if:
 *   - it's "Reorder Now" in `current`, AND
 *   - it either didn't exist in `previous` at all, or existed with a
 *     different (non-"Reorder Now") status.
 *
 * Pure function, no I/O — the database lookup for "what was the
 * previous dataset" lives in repository.ts, kept separate exactly like
 * every other analytics function in this project (classify.ts,
 * summary.ts) that computes from data it's simply given.
 */
export function findNewlyAtRisk(previous: ClassifiedSku[] | null, current: ClassifiedSku[]): ClassifiedSku[] {
  const previousStatusBySku = new Map<string, string>();
  if (previous) {
    for (const row of previous) {
      previousStatusBySku.set(row.sku, row.stock_status);
    }
  }

  return current.filter((row) => {
    if (row.stock_status !== "Reorder Now") return false;
    const previousStatus = previousStatusBySku.get(row.sku);
    return previousStatus === undefined || previousStatus !== "Reorder Now";
  });
}

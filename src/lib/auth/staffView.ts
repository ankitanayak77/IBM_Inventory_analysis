import type { AnalysisResult } from "@/lib/analytics/analyze";
import type { ClassifiedSku } from "@/lib/analytics/types";

/**
 * Report FR-9: "store staff sees only their reorder task list." Strips a
 * full AnalysisResult down to just that — no KPIs, no FSN/ABC breakdowns,
 * no Pareto/category charts, no full SKU list. Applied server-side, in
 * the route handler, before the response is ever serialized — not a
 * client-side UI restriction that a staff account could bypass by
 * reading the raw API response directly.
 */
export interface StaffTaskListView {
  role: "staff";
  sourceLabel: string;
  reorderRisk: ClassifiedSku[];
}

export function toStaffView(result: AnalysisResult, sourceLabel: string): StaffTaskListView {
  return {
    role: "staff",
    sourceLabel,
    reorderRisk: result.reorderRisk,
  };
}

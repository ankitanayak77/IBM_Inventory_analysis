import { NextResponse } from "next/server";
import { loadAndClassifySampleData } from "@/lib/analytics/loadSampleData";
import { requireRole } from "@/lib/auth/session";
import { toStaffView } from "@/lib/auth/staffView";

/**
 * GET /api/analysis/summary
 * Report Section 7.3 — returns the full analysis (KPIs, FSN/ABC breakdowns,
 * Pareto rollup, category performance, the priority matrix, and the
 * reorder-risk list) for the bundled sample dataset — for an owner_manager.
 * A staff account gets the restricted view (Report FR-9): reorder task
 * list only, enforced server-side before serialization, not a client-side
 * UI restriction. See /api/upload for the same shape from an uploaded CSV.
 */
export async function GET() {
  const auth = await requireRole();
  if (!auth.ok) {
    return NextResponse.json({ error: auth.error }, { status: auth.status! });
  }

  const result = loadAndClassifySampleData();

  if (auth.user!.role === "staff") {
    return NextResponse.json(toStaffView(result, "sample dataset"));
  }

  return NextResponse.json({
    ...result,
    rejectedRowCount: result.rejected.length,
    skuCount: result.rows.length,
  });
}

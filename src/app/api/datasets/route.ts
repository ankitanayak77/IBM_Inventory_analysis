import { NextResponse } from "next/server";
import { listDatasets } from "@/db/repository";
import { requireRole } from "@/lib/auth/session";

/**
 * GET /api/datasets
 * Report Chapter 15 / Phase 2 — "persisted history". Lists past analysis
 * runs (each CSV upload or the bundled sample, when a database is
 * configured) so a returning user can see what they've analyzed before,
 * not just whatever is currently loaded in the browser tab.
 *
 * Returns an empty list (not an error) when no database is configured —
 * Phase 2 is additive, same principle as /api/upload's optional
 * persistence: a person who hasn't set up Postgres yet still gets a
 * working response, just with nothing to list.
 *
 * Report FR-9 — owner_manager only. Browsing upload history isn't part of
 * "staff sees only their reorder task list" (Report FR-9's exact phrasing
 * is singular — the current list, not a history browser); staff gets the
 * current reorder list via /api/analysis/summary or /api/datasets/[id]
 * instead, both of which return the restricted view for them.
 */
export async function GET() {
  const auth = await requireRole(["owner_manager"]);
  if (!auth.ok) {
    return NextResponse.json({ error: auth.error }, { status: auth.status! });
  }

  if (!process.env.DATABASE_URL) {
    return NextResponse.json({ datasets: [], databaseConfigured: false });
  }

  try {
    const datasets = await listDatasets();
    return NextResponse.json({ datasets, databaseConfigured: true });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Failed to list datasets.";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

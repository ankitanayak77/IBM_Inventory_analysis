import { NextResponse } from "next/server";
import { getSkuHistory } from "@/db/repository";
import { requireRole } from "@/lib/auth/session";

/**
 * GET /api/sku/[sku]/history
 * Report Section 7.5 ("SKU Detail... with its full sales history"),
 * built as a genuine time series across every persisted dataset that
 * contains this SKU — something the original report scoped only as a
 * single-snapshot view, since real persistence (Phase 2) didn't exist
 * yet when that chapter was written.
 *
 * Report FR-9 — owner_manager only, same reasoning as /api/datasets (the
 * history list): drilling into a SKU's trend across uploads is a manager
 * analysis action, not part of "staff sees only their reorder task list."
 *
 * Gracefully returns an empty history (not an error) when no database is
 * configured — the same optional-additive pattern as /api/datasets,
 * since Phase 2 persistence itself is optional.
 */
export async function GET(_request: Request, { params }: { params: Promise<{ sku: string }> }) {
  const auth = await requireRole(["owner_manager"]);
  if (!auth.ok) {
    return NextResponse.json({ error: auth.error }, { status: auth.status! });
  }

  const { sku } = await params;

  if (!process.env.DATABASE_URL) {
    return NextResponse.json({ sku, history: [], databaseConfigured: false });
  }

  try {
    const history = await getSkuHistory(sku);
    return NextResponse.json({ sku, history, databaseConfigured: true });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Failed to load SKU history.";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

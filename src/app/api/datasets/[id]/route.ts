import { NextResponse } from "next/server";
import { loadDataset } from "@/db/repository";
import { requireRole } from "@/lib/auth/session";
import { toStaffView } from "@/lib/auth/staffView";

/**
 * GET /api/datasets/[id]
 * Loads one persisted analysis run back in full (same AnalysisResult
 * shape as /api/upload and /api/analysis/summary), so the dashboard can
 * show a past upload exactly as it looked when it was analyzed.
 *
 * Report FR-9 — any authenticated user, but a staff session gets the
 * restricted view (reorder task list only), same restriction as
 * /api/analysis/summary, enforced server-side before serialization.
 */
export async function GET(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const auth = await requireRole();
  if (!auth.ok) {
    return NextResponse.json({ error: auth.error }, { status: auth.status! });
  }

  if (!process.env.DATABASE_URL) {
    return NextResponse.json({ error: "No database is configured." }, { status: 503 });
  }

  const { id } = await params;
  const datasetId = Number(id);
  if (!Number.isInteger(datasetId) || datasetId <= 0) {
    return NextResponse.json({ error: `"${id}" is not a valid dataset id.` }, { status: 400 });
  }

  try {
    const result = await loadDataset(datasetId);
    if (!result) {
      return NextResponse.json({ error: `No dataset found with id ${datasetId}.` }, { status: 404 });
    }
    if (auth.user!.role === "staff") {
      return NextResponse.json(toStaffView(result, result.sourceLabel));
    }
    return NextResponse.json(result);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Failed to load dataset.";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

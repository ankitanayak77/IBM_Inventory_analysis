import { NextResponse } from "next/server";
import { loadAndClassifySampleData } from "@/lib/analytics/loadSampleData";
import { loadDataset } from "@/db/repository";
import { requireRole } from "@/lib/auth/session";

/**
 * GET /api/analysis/recommendations?datasetId=123
 * Returns algorithmic inventory recommendations, executive report metrics,
 * stockout replenishment plans, dead stock liquidation, and supplier risk analysis.
 *
 * RBAC:
 * - owner_manager: receives full InventoryRecommendationsSummary (health score,
 *   financial impact, trapped capital, all recommendation types, supplier risk).
 * - staff: receives filtered replenishment-only recommendations matching their
 *   operational reorder task list.
 */
export async function GET(request: Request) {
  const auth = await requireRole();
  if (!auth.ok) {
    return NextResponse.json({ error: auth.error }, { status: auth.status! });
  }

  const { searchParams } = new URL(request.url);
  const datasetIdParam = searchParams.get("datasetId");

  let result;
  let sourceLabel = "sample dataset";

  if (datasetIdParam) {
    const id = parseInt(datasetIdParam, 10);
    if (isNaN(id)) {
      return NextResponse.json({ error: "Invalid datasetId parameter" }, { status: 400 });
    }
    const loaded = await loadDataset(id);
    if (!loaded) {
      return NextResponse.json({ error: `Dataset ${id} not found` }, { status: 404 });
    }
    result = loaded;
    sourceLabel = loaded.sourceLabel;
  } else {
    result = loadAndClassifySampleData();
  }

  const { recommendations } = result;

  if (auth.user!.role === "staff") {
    // Staff gets only replenishment actions
    const staffItems = recommendations.items.filter((i) => i.type === "replenishment");
    return NextResponse.json({
      role: "staff",
      sourceLabel,
      items: staffItems,
      immediateActionCount: staffItems.filter((i) => i.urgency === "Immediate").length,
    });
  }

  return NextResponse.json({
    role: "owner_manager",
    sourceLabel,
    ...recommendations,
  });
}

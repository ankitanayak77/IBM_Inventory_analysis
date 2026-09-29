import { renderToBuffer } from "@react-pdf/renderer";
import { InventoryReportPdf } from "@/lib/export/InventoryReportPdf";
import type { AnalysisResult } from "@/lib/analytics/analyze";
import { requireRole } from "@/lib/auth/session";

/**
 * POST /api/export/pdf
 * Report FR-8 ("...as CSV or PDF"), the PDF half. CSV export (toCsv.ts)
 * runs client-side since the data's already in the browser; PDF rendering
 * runs server-side in this Route Handler instead, because @react-pdf/renderer
 * pulls in a real layout engine that's better kept out of the client bundle,
 * and because a Route Handler is trivially testable here with a real
 * Request/Response — matching the pattern already established for
 * /api/upload (a Route Handler, not a Server Action, for the same reasons:
 * see that route's comment on the Server Action body-size-limit issue).
 *
 * The client sends back the *already-computed* AnalysisResult it currently
 * has in state (sample or uploaded) — this route does not re-run
 * classification, it only renders whatever the client is already looking
 * at, so the PDF can never show different numbers than the dashboard.
 *
 * Report FR-9 — owner_manager only, same reasoning as /api/upload: a full
 * report export is a manager action.
 */
export async function POST(request: Request) {
  const auth = await requireRole(["owner_manager"]);
  if (!auth.ok) {
    return new Response(JSON.stringify({ error: auth.error }), {
      status: auth.status!,
      headers: { "Content-Type": "application/json" },
    });
  }

  let body: { result?: AnalysisResult; sourceLabel?: string };
  try {
    body = await request.json();
  } catch {
    return new Response(JSON.stringify({ error: "Request body was not valid JSON." }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  const { result, sourceLabel } = body;
  if (!result || !Array.isArray(result.rows) || !result.kpis) {
    return new Response(
      JSON.stringify({ error: "Request body must include a full AnalysisResult under `result`." }),
      { status: 400, headers: { "Content-Type": "application/json" } }
    );
  }

  let pdfBuffer: Buffer;
  try {
    pdfBuffer = await renderToBuffer(
      <InventoryReportPdf result={result} sourceLabel={sourceLabel ?? "uploaded data"} />
    );
  } catch (err) {
    const message = err instanceof Error ? err.message : "PDF rendering failed.";
    return new Response(JSON.stringify({ error: message }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }

  return new Response(new Uint8Array(pdfBuffer), {
    status: 200,
    headers: {
      "Content-Type": "application/pdf",
      "Content-Disposition": 'attachment; filename="inventory-analysis-report.pdf"',
      "Content-Length": String(pdfBuffer.length),
    },
  });
}

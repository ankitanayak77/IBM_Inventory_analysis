import { NextResponse } from "next/server";
import { analyzeCsvText } from "@/lib/analytics/analyze";
import { saveAnalysisResult, getPreviousDatasetRows } from "@/db/repository";
import { requireRole } from "@/lib/auth/session";
import { findNewlyAtRisk } from "@/lib/analytics/compareDatasets";
import { sendNewlyAtRiskEmail } from "@/lib/alerts/sendNewlyAtRiskEmail";
import type { ClassifiedSku } from "@/lib/analytics/types";

// A real API route handler (not a Server Action) — deliberately, per the
// documented Next.js issue where Server Actions impose a hard-to-configure
// 1MB body-size limit on multipart form submissions (tracked upstream in
// vercel/next.js#49891, #59277, #77505; still reported unresolved in
// production as of the most recent linked discussion). Route handlers use
// the standard Fetch API Request/Response and carry no such Next-specific
// cap. The realistic ceiling here is the hosting platform's own request
// body limit (e.g. ~4.5MB on Vercel serverless functions) — comfortably
// above even a 10,000-SKU CSV (Report NFR target, Section 6.2), which is
// on the order of 1–2MB at this schema's row width.
const MAX_UPLOAD_BYTES = 4 * 1024 * 1024; // stay well under the ~4.5MB platform ceiling

/**
 * POST /api/upload
 * Accepts a multipart/form-data request with a "file" field (a CSV
 * matching the schema in Report Section 3.1), runs it through the same
 * `analyzeCsvText` pipeline as the sample-data page, and returns the full
 * AnalysisResult as JSON — this is Report FR-1 ("Import stock & sales data
 * from CSV upload") made real, not just validated in a unit test.
 *
 * Report FR-9 — owner_manager only. Uploading new data / running a fresh
 * analysis is a manager action, not a store-staff one (staff sees only
 * their reorder task list — see /api/analysis/summary and
 * /api/datasets/[id] for where that restriction is enforced instead).
 */
export async function POST(request: Request) {
  const auth = await requireRole(["owner_manager"]);
  if (!auth.ok) {
    return NextResponse.json({ error: auth.error }, { status: auth.status! });
  }

  let formData: FormData;
  try {
    formData = await request.formData();
  } catch {
    return NextResponse.json({ error: "Request was not valid multipart/form-data." }, { status: 400 });
  }

  const file = formData.get("file");
  if (!(file instanceof File)) {
    return NextResponse.json({ error: 'No file found under the "file" field.' }, { status: 400 });
  }

  if (file.size === 0) {
    return NextResponse.json({ error: "The uploaded file is empty." }, { status: 400 });
  }
  if (file.size > MAX_UPLOAD_BYTES) {
    return NextResponse.json(
      { error: `File is ${(file.size / 1024 / 1024).toFixed(1)}MB, which exceeds the ${MAX_UPLOAD_BYTES / 1024 / 1024}MB limit for this endpoint.` },
      { status: 413 }
    );
  }

  const csvText = await file.text();

  let result;
  try {
    result = analyzeCsvText(csvText);
  } catch (err) {
    // analyzeCsvText only throws when the CSV header itself is missing a
    // required column (Report Section 3.1 schema) — everything row-level
    // is collected as `rejected` instead, never thrown.
    const message = err instanceof Error ? err.message : "Failed to parse the uploaded CSV.";
    return NextResponse.json({ error: message }, { status: 400 });
  }

  if (result.rows.length === 0) {
    return NextResponse.json(
      {
        error: "Every row in the uploaded file was rejected — nothing to analyze.",
        rejected: result.rejected,
      },
      { status: 422 }
    );
  }

  // Persistence (Phase 2) is optional, not required: if DATABASE_URL isn't
  // configured, upload/analyze must keep working exactly as it did in
  // Phases 0-1 — this is an additive feature, never a hard dependency.
  // A save failure (DB unreachable, etc.) is logged but does not fail the
  // request: the person still gets their analysis even if history
  // couldn't be recorded this time.
  //
  // Report FR-10 ("send an alert... when a SKU newly crosses into
  // 'Reorder Now'"): the in-app half is computed whenever persistence
  // succeeds. The email half fires right after, gated behind
  // RESEND_API_KEY + RESEND_ALERT_TO both being set (sendNewlyAtRiskEmail
  // itself no-ops cleanly if either is missing) — same optional-additive
  // pattern as DATABASE_URL, since email is a genuinely optional
  // notification channel, never a hard requirement for upload to work.
  let datasetId: number | null = null;
  let newlyAtRisk: ClassifiedSku[] | null = null;
  let emailAlert: { sent: boolean; skipReason?: string; error?: string } | null = null;
  if (process.env.DATABASE_URL) {
    try {
      const saved = await saveAnalysisResult(result, file.name);
      datasetId = saved.datasetId;
      const previousRows = await getPreviousDatasetRows(datasetId);
      newlyAtRisk = findNewlyAtRisk(previousRows, result.rows);

      const emailResult = await sendNewlyAtRiskEmail(newlyAtRisk, file.name);
      emailAlert = { sent: emailResult.sent, skipReason: emailResult.skipReason, error: emailResult.error };
      if (!emailResult.sent && emailResult.error) {
        console.error("Failed to send newly-at-risk alert email:", emailResult.error);
      }
    } catch (err) {
      console.error("Failed to persist analysis result:", err);
    }
  }

  return NextResponse.json({
    ...result,
    rejectedRowCount: result.rejected.length,
    skuCount: result.rows.length,
    datasetId,
    newlyAtRisk,
    emailAlert,
  });
}

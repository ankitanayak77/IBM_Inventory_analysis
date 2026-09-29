import { Resend } from "resend";
import type { ClassifiedSku } from "@/lib/analytics/types";

/**
 * Report FR-10, the email half. Confirmed via the installed package's
 * own type definitions (node_modules/resend/dist/index.d.mts) and
 * cross-checked against 6 independent, currently-dated Resend docs
 * sources before writing this:
 *
 *  - resend.emails.send() returns { data, error } — it does NOT throw on
 *    API-level failures (bad key, unverified domain, rate limit). A
 *    try/catch alone would silently miss those; `error` must be checked
 *    explicitly. A network-level failure (DNS, connection refused) can
 *    still throw, so both are handled here.
 *  - The zero-setup sender `onboarding@resend.dev` only works for
 *    sending TO the email address on the Resend account itself — sending
 *    to anyone else with it returns a 403. That's why RESEND_ALERT_TO
 *    below must be that same account's email until a custom domain is
 *    verified at resend.com/domains (then RESEND_FROM_EMAIL can become a
 *    real branded address and RESEND_ALERT_TO can be anyone).
 *
 * Gated behind RESEND_API_KEY existing, the same optional-additive
 * pattern as DATABASE_URL and the in-app half of this same feature: a
 * missing key must never break the upload flow that already works
 * without it.
 */

export interface SendAlertResult {
  sent: boolean;
  skipReason?: string;
  emailId?: string;
  error?: string;
}

function buildAlertHtml(skus: ClassifiedSku[], sourceLabel: string): string {
  const rows = skus
    .map(
      (r) =>
        `<tr>
          <td style="padding:6px 10px;border-bottom:1px solid #e2e8f0;">${escapeHtml(r.sku)}</td>
          <td style="padding:6px 10px;border-bottom:1px solid #e2e8f0;">${escapeHtml(r.product_name)} (${escapeHtml(r.size)})</td>
          <td style="padding:6px 10px;border-bottom:1px solid #e2e8f0;text-align:right;">${r.quantity_on_hand}</td>
          <td style="padding:6px 10px;border-bottom:1px solid #e2e8f0;text-align:right;">${r.reorder_point}</td>
        </tr>`
    )
    .join("");

  return `
    <div style="font-family:sans-serif;color:#1a1a1a;">
      <h2 style="color:#0F1F3D;">Inventory Analysis — Reorder Alert</h2>
      <p>${skus.length} SKU${skus.length === 1 ? "" : "s"} newly crossed into <strong>"Reorder Now"</strong> in the latest upload (<em>${escapeHtml(sourceLabel)}</em>).</p>
      <table style="border-collapse:collapse;width:100%;margin-top:12px;">
        <thead>
          <tr style="background:#0F1F3D;color:#fff;">
            <th style="padding:6px 10px;text-align:left;">SKU</th>
            <th style="padding:6px 10px;text-align:left;">Product</th>
            <th style="padding:6px 10px;text-align:right;">On hand</th>
            <th style="padding:6px 10px;text-align:right;">Reorder point</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
}

function escapeHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

/**
 * Sends the "newly at risk" alert email. Returns a result object rather
 * than throwing on a skip/failure, so the caller (/api/upload) can log
 * or surface it without wrapping every call site in its own try/catch —
 * matching how the rest of this codebase's optional features degrade
 * (see saveAnalysisResult's caller in upload/route.ts for the same shape
 * of decision).
 */
export async function sendNewlyAtRiskEmail(skus: ClassifiedSku[], sourceLabel: string): Promise<SendAlertResult> {
  if (skus.length === 0) {
    return { sent: false, skipReason: "No newly-at-risk SKUs to report." };
  }
  if (!process.env.RESEND_API_KEY) {
    return { sent: false, skipReason: "RESEND_API_KEY is not set." };
  }
  const to = process.env.RESEND_ALERT_TO;
  if (!to) {
    return { sent: false, skipReason: "RESEND_ALERT_TO is not set (who should receive the alert)." };
  }
  const from = process.env.RESEND_FROM_EMAIL || "onboarding@resend.dev";

  try {
    const resend = new Resend(process.env.RESEND_API_KEY);
    const { data, error } = await resend.emails.send({
      from,
      to,
      subject: `Inventory Analysis: ${skus.length} SKU${skus.length === 1 ? "" : "s"} newly at risk`,
      html: buildAlertHtml(skus, sourceLabel),
    });

    if (error) {
      return { sent: false, error: `${error.name}: ${error.message}` };
    }
    return { sent: true, emailId: data?.id };
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error calling Resend.";
    return { sent: false, error: message };
  }
}

"use client";

import type { ClassifiedSku } from "@/lib/analytics/types";

interface EmailAlertStatus {
  sent: boolean;
  skipReason?: string;
  error?: string;
}

/**
 * Report FR-10: "send an alert (email or in-app)... when a SKU newly
 * crosses into 'Reorder Now.'" This is the in-app half — a dismissible
 * banner surfacing exactly the SKUs findNewlyAtRisk() flagged, right
 * after an upload, so the transition is visible the moment it happens
 * rather than requiring someone to notice it buried in the full reorder
 * list. `emailAlert` (when provided) surfaces whether the email half
 * (sendNewlyAtRiskEmail, gated behind RESEND_API_KEY/RESEND_ALERT_TO)
 * actually fired — sent, skipped (not configured), or failed — rather
 * than leaving that outcome silent.
 */
export function NewlyAtRiskBanner({
  skus,
  emailAlert,
  onDismiss,
}: {
  skus: ClassifiedSku[];
  emailAlert?: EmailAlertStatus | null;
  onDismiss: () => void;
}) {
  if (skus.length === 0) return null;

  return (
    <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start justify-between gap-4">
      <div>
        <div className="text-sm font-semibold text-red-800">
          {skus.length} SKU{skus.length === 1 ? "" : "s"} newly crossed into &quot;Reorder Now&quot; since your last
          upload
        </div>
        <ul className="mt-1 text-sm text-red-700 space-y-0.5">
          {skus.map((r) => (
            <li key={r.sku}>
              {r.product_name} ({r.size}) — {r.quantity_on_hand} on hand / {r.reorder_point} reorder point
            </li>
          ))}
        </ul>
        {emailAlert && (
          <div className="mt-2 text-xs text-red-500">
            {emailAlert.sent && "✓ Email alert sent."}
            {!emailAlert.sent && emailAlert.skipReason && `Email alert not sent: ${emailAlert.skipReason}`}
            {!emailAlert.sent && emailAlert.error && `Email alert failed: ${emailAlert.error}`}
          </div>
        )}
      </div>
      <button onClick={onDismiss} className="text-red-400 hover:text-red-600 text-sm shrink-0">
        Dismiss
      </button>
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import type { ClassifiedSku } from "@/lib/analytics/types";

interface SkuHistoryEntry {
  datasetId: number;
  sourceLabel: string;
  uploadedAt: string;
  record: ClassifiedSku;
}

function money(n: number): string {
  return `$${n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

const statusColor: Record<string, string> = {
  "Reorder Now": "bg-red-100 text-red-800 border-red-300",
  "Low - Monitor": "bg-amber-100 text-amber-800 border-amber-300",
  Healthy: "bg-emerald-100 text-emerald-800 border-emerald-300",
};

/**
 * Report Section 7.5 ("SKU Detail... with its full sales history").
 * The current snapshot renders instantly from `sku` — already in the
 * dashboard's in-memory state, no API call needed for that part. Only
 * the historical trend across past uploads needs a real request, since
 * that data lives in the database, not the browser.
 */
export function SkuDetailPanel({ sku, onClose }: { sku: ClassifiedSku; onClose: () => void }) {
  const [history, setHistory] = useState<SkuHistoryEntry[] | null>(null);
  const [databaseConfigured, setDatabaseConfigured] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`/api/sku/${encodeURIComponent(sku.sku)}/history`)
      .then((r) => r.json())
      .then((body) => {
        if (body.error) {
          setError(body.error);
          return;
        }
        setDatabaseConfigured(body.databaseConfigured);
        setHistory(body.history ?? []);
      })
      .catch(() => setError("Could not load history."));
  }, [sku.sku]);

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-6 z-50" onClick={onClose}>
      <div
        className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[85vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="bg-[var(--color-navy)] text-white px-6 py-4 flex items-center justify-between sticky top-0">
          <div>
            <h2 className="text-lg font-bold">
              {sku.product_name} ({sku.size})
            </h2>
            <p className="text-xs text-slate-300 font-mono">{sku.sku}</p>
          </div>
          <button onClick={onClose} className="text-slate-300 hover:text-white text-xl leading-none">
            ×
          </button>
        </div>

        <div className="p-6 space-y-6">
          <section>
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Current snapshot</h3>
            <div className="grid grid-cols-2 gap-3">
              {[
                ["Category / Supplier", `${sku.category} · ${sku.supplier}`],
                ["Color / Season", `${sku.color} · ${sku.season}`],
                ["On hand / Reorder point", `${sku.quantity_on_hand} / ${sku.reorder_point}`],
                ["Units sold (30d)", sku.units_sold_30d.toString()],
                ["Cost / Retail price", `${money(sku.cost_per_unit)} / ${money(sku.retail_price)}`],
                ["Inventory value", money(sku.inventory_value)],
                ["Revenue (30d)", money(sku.revenue_30d)],
                [
                  "Turnover ratio (ITR)",
                  Number.isFinite(sku.itr_annualised) ? `${sku.itr_annualised.toFixed(1)}×` : "∞ (out of stock, still selling)",
                ],
                ["Days of stock left", Number.isFinite(sku.days_of_stock) ? `${sku.days_of_stock.toFixed(0)}d` : "∞"],
                ["FSN / ABC class", `${sku.fsn_class} / ${sku.abc_class}`],
                ["Priority", sku.priority_tag],
              ].map(([label, value]) => (
                <div key={label} className="bg-slate-50 rounded-md p-2.5">
                  <div className="text-[10px] text-slate-500 uppercase">{label}</div>
                  <div className="text-sm font-medium text-[var(--color-navy)] mt-0.5">{value}</div>
                </div>
              ))}
              <div className="bg-slate-50 rounded-md p-2.5 col-span-2">
                <div className="text-[10px] text-slate-500 uppercase">Stock status</div>
                <span className={`inline-block mt-1 px-2 py-0.5 rounded-full text-xs border ${statusColor[sku.stock_status]}`}>
                  {sku.stock_status}
                </span>
              </div>
            </div>
          </section>

          <section>
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
              Upload history for this SKU
            </h3>
            {error && <p className="text-sm text-red-600">{error}</p>}
            {!error && history === null && <p className="text-sm text-slate-400">Loading…</p>}
            {!error && history !== null && databaseConfigured === false && (
              <p className="text-sm text-slate-500">
                No database is configured for this deployment, so historical trend data isn&apos;t available — only
                the current snapshot above.
              </p>
            )}
            {!error && history !== null && databaseConfigured && history.length === 0 && (
              <p className="text-sm text-slate-500">
                This is the first time this SKU has been seen in an uploaded dataset.
              </p>
            )}
            {!error && history !== null && history.length > 0 && (
              <div className="border border-slate-200 rounded-md overflow-hidden">
                <table className="w-full text-xs">
                  <thead className="bg-slate-50 text-slate-500">
                    <tr>
                      <th className="text-left px-3 py-1.5">Source</th>
                      <th className="text-left px-3 py-1.5">Uploaded</th>
                      <th className="text-right px-3 py-1.5">On hand</th>
                      <th className="text-right px-3 py-1.5">Sold (30d)</th>
                      <th className="text-center px-3 py-1.5">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.map((h) => (
                      <tr key={h.datasetId} className="border-t border-slate-100">
                        <td className="px-3 py-1.5">{h.sourceLabel}</td>
                        <td className="px-3 py-1.5">{new Date(h.uploadedAt).toLocaleDateString()}</td>
                        <td className="text-right px-3 py-1.5">{h.record.quantity_on_hand}</td>
                        <td className="text-right px-3 py-1.5">{h.record.units_sold_30d}</td>
                        <td className="text-center px-3 py-1.5">
                          <span className={`px-1.5 py-0.5 rounded-full border ${statusColor[h.record.stock_status]}`}>
                            {h.record.stock_status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}

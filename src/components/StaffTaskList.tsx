"use client";

import type { StaffTaskListView } from "@/lib/auth/staffView";
import { SignOutButton } from "@/components/SignOutButton";
import { calculateSuggestedOrderQty } from "@/lib/analytics/recommendations";

const statusColor: Record<string, string> = {
  "Reorder Now": "bg-red-100 text-red-800 border-red-300",
  "Low - Monitor": "bg-amber-100 text-amber-800 border-amber-300",
};

/**
 * Report FR-9: "store staff sees only their reorder task list." A
 * deliberately separate, simpler component from Dashboard.tsx — not the
 * same component with role checks sprinkled through it — because staff
 * genuinely get a different, smaller product surface (no KPIs, no
 * upload, no export, no history), not just a filtered version of the
 * manager one.
 */
export function StaffTaskList({ data, userName }: { data: StaffTaskListView; userName: string }) {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-[var(--color-navy)] text-white px-8 py-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Reorder Task List</h1>
          <p className="text-sm text-slate-300 mt-1">
            {userName} · source: {data.sourceLabel}
          </p>
        </div>
        <SignOutButton />
      </header>

      <main className="p-8 max-w-3xl mx-auto space-y-4">
        {data.reorderRisk.length === 0 ? (
          <div className="bg-white rounded-lg border border-slate-200 p-6 shadow-sm text-sm text-slate-500">
            Nothing needs reordering right now.
          </div>
        ) : (
          data.reorderRisk.map((r) => {
            const soq = calculateSuggestedOrderQty(r.quantity_on_hand, r.reorder_point, r.units_sold_30d);
            return (
              <div key={r.sku} className="bg-white rounded-lg border border-slate-200 p-4 shadow-sm flex items-center justify-between">
                <div>
                  <div className="font-medium text-[var(--color-navy)]">
                    {r.product_name} ({r.size})
                  </div>
                  <div className="text-xs text-slate-500 mt-0.5">
                    {r.sku} · On hand: <strong>{r.quantity_on_hand}</strong> / ROP: {r.reorder_point} · Supplier: {r.supplier}
                  </div>
                  <div className="text-xs font-semibold text-amber-900 bg-amber-50 px-2 py-0.5 rounded mt-2 inline-block border border-amber-200">
                    Suggested Reorder: {soq} units ({Number.isFinite(r.days_of_stock) ? `${r.days_of_stock.toFixed(0)}d runway` : "out of stock"})
                  </div>
                </div>
                <span className={`px-2.5 py-1 rounded-full text-xs font-semibold border ${statusColor[r.stock_status] ?? ""}`}>
                  {r.stock_status}
                </span>
              </div>
            );
          })
        )}
      </main>
    </div>
  );
}

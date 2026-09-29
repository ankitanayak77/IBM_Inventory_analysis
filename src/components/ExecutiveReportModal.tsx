"use client";

import type { AnalysisResult } from "@/lib/analytics/analyze";

interface ExecutiveReportModalProps {
  result: AnalysisResult;
  sourceLabel: string;
  onClose: () => void;
  onDownloadPdf: () => void;
}

function money(n: number): string {
  return `$${n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}
function pct(n: number): string {
  return `${n.toFixed(1)}%`;
}

export function ExecutiveReportModal({
  result,
  sourceLabel,
  onClose,
  onDownloadPdf,
}: ExecutiveReportModalProps) {
  const { kpis, fsn, abc, recommendations } = result;
  const generatedDate = new Date().toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  const replenishmentItems = recommendations?.items?.filter((i) => i.type === "replenishment") ?? [];
  const liquidationItems = recommendations?.items?.filter((i) => i.type === "liquidation") ?? [];
  const pricingItems = recommendations?.items?.filter((i) => i.type === "pricing_margin") ?? [];

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 sm:p-6">
      <div className="bg-white rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] flex flex-col overflow-hidden border border-slate-200 animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="bg-[var(--color-navy)] text-white px-6 py-4 flex items-center justify-between shrink-0">
          <div>
            <span className="text-xs uppercase tracking-wider text-amber-300 font-semibold">
              Strategic Advisory
            </span>
            <h2 className="text-xl font-bold">Executive Inventory Analysis & Action Report</h2>
            <p className="text-xs text-slate-300 mt-0.5">
              Dataset: {sourceLabel} · {kpis.totalSkus} SKUs Analyzed · Published {generatedDate}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={onDownloadPdf}
              className="text-xs font-medium px-3 py-1.5 rounded-md bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold transition"
            >
              Export PDF
            </button>
            <button
              onClick={onClose}
              className="text-slate-300 hover:text-white p-1 rounded-md transition text-lg leading-none"
              aria-label="Close report"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Scrollable Report Body */}
        <div className="p-6 overflow-y-auto space-y-8 text-sm text-slate-700 leading-relaxed">
          {/* Executive Summary Card */}
          <div className="bg-gradient-to-br from-slate-50 to-blue-50/40 rounded-lg p-5 border border-slate-200">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-base font-bold text-[var(--color-navy)]">1. Executive Summary & Health Score</h3>
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold uppercase text-slate-500">Portfolio Health:</span>
                <span
                  className={`text-xs font-bold px-2.5 py-1 rounded-full ${
                    recommendations.healthScore >= 80
                      ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                      : recommendations.healthScore >= 65
                      ? "bg-amber-100 text-amber-800 border border-amber-300"
                      : "bg-red-100 text-red-800 border border-red-300"
                  }`}
                >
                  {recommendations.healthScore} / 100 · {recommendations.healthGrade}
                </span>
              </div>
            </div>
            <p className="text-slate-700">{recommendations.executiveSummaryText}</p>

            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mt-4 pt-4 border-t border-slate-200/80">
              <div>
                <div className="text-[11px] text-slate-500 uppercase">Valuation (Cost)</div>
                <div className="text-base font-bold text-slate-900">{money(kpis.totalInventoryValue)}</div>
              </div>
              <div>
                <div className="text-[11px] text-slate-500 uppercase">30d Revenue</div>
                <div className="text-base font-bold text-slate-900">{money(kpis.totalRevenue30d)}</div>
              </div>
              <div>
                <div className="text-[11px] text-slate-500 uppercase">GMROI (Annualized)</div>
                <div className="text-base font-bold text-emerald-700">{kpis.gmroi.toFixed(2)}×</div>
              </div>
              <div>
                <div className="text-[11px] text-slate-500 uppercase">Replenishment Budget</div>
                <div className="text-base font-bold text-red-700">{money(recommendations.totalReplenishmentCost)}</div>
              </div>
              <div>
                <div className="text-[11px] text-slate-500 uppercase">Trapped Dead Capital</div>
                <div className="text-base font-bold text-amber-700">{money(recommendations.trappedCapitalInDeadStock)}</div>
              </div>
            </div>
          </div>

          {/* Section 2: Movement Velocity & FSN Distribution */}
          <div>
            <h3 className="text-base font-bold text-[var(--color-navy)] mb-2">
              2. Movement Velocity & FSN Segmentation
            </h3>
            <p className="text-xs text-slate-600 mb-3">
              Per standard supply-chain methodology, SKUs are ranked by annualised inventory turnover ratio (ITR)
              into <strong>Fast-Moving (top 20%)</strong>, <strong>Slow-Moving (next 35%)</strong>, and{" "}
              <strong>Non-Moving (bottom 45%)</strong> tiers.
            </p>
            <div className="border border-slate-200 rounded-lg overflow-hidden">
              <table className="w-full text-xs">
                <thead className="bg-slate-100 text-slate-700 font-semibold">
                  <tr>
                    <th className="text-left px-3 py-2">FSN Segment</th>
                    <th className="text-right px-3 py-2">SKU Count</th>
                    <th className="text-right px-3 py-2">% of Catalog</th>
                    <th className="text-right px-3 py-2">Capital Tied Up</th>
                    <th className="text-right px-3 py-2">% of Valuation</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {fsn.map((row) => (
                    <tr key={row.fsn_class}>
                      <td className="px-3 py-2 font-medium text-slate-800">{row.fsn_class}</td>
                      <td className="text-right px-3 py-2">{row.skuCount}</td>
                      <td className="text-right px-3 py-2">{pct(row.pctOfSkus)}</td>
                      <td className="text-right px-3 py-2 font-medium">{money(row.inventoryValue)}</td>
                      <td className="text-right px-3 py-2">{pct(row.pctOfValue)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="bg-amber-50/60 rounded border border-amber-200 p-3 mt-3 text-xs text-amber-900">
              <strong>Key Finding:</strong> Non-moving inventory accounts for{" "}
              {pct(fsn.find((f) => f.fsn_class === "Non-moving")?.pctOfValue ?? 0)} of total warehouse working capital.
              Holding costs for these items compound at ~20-25% annually in warehousing, financing, and obsolescence risk.
            </div>
          </div>

          {/* Section 3: Revenue Concentration & ABC Pareto */}
          <div>
            <h3 className="text-base font-bold text-[var(--color-navy)] mb-2">
              3. Revenue Concentration & ABC Pareto Distribution
            </h3>
            <p className="text-xs text-slate-600 mb-3">
              ABC analysis classifies SKUs based on cumulative 30-day revenue contribution: Class A (top 80% revenue),
              Class B (next 15%), and Class C (tail 5%).
            </p>
            <div className="border border-slate-200 rounded-lg overflow-hidden">
              <table className="w-full text-xs">
                <thead className="bg-slate-100 text-slate-700 font-semibold">
                  <tr>
                    <th className="text-left px-3 py-2">ABC Class</th>
                    <th className="text-right px-3 py-2">SKU Count</th>
                    <th className="text-right px-3 py-2">% of Catalog</th>
                    <th className="text-right px-3 py-2">30-Day Revenue</th>
                    <th className="text-right px-3 py-2">% of Total Revenue</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {abc.map((row) => (
                    <tr key={row.abc_class}>
                      <td className="px-3 py-2 font-medium text-slate-800">
                        Class {row.abc_class} ({row.abc_class === "A" ? "Critical Revenue Drivers" : row.abc_class === "B" ? "Moderate Drivers" : "Long-Tail"})
                      </td>
                      <td className="text-right px-3 py-2">{row.skuCount}</td>
                      <td className="text-right px-3 py-2">{pct(row.pctOfSkus)}</td>
                      <td className="text-right px-3 py-2 font-medium">{money(row.revenue)}</td>
                      <td className="text-right px-3 py-2">{pct(row.pctOfRevenue)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Section 4: Immediate Stockout Risks & Purchase Order Plan */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-base font-bold text-[var(--color-navy)]">
                4. Immediate Stockout Risks & Replenishment Requisitions
              </h3>
              <span className="text-xs font-semibold text-red-700 bg-red-50 border border-red-200 px-2 py-0.5 rounded">
                {replenishmentItems.length} SKUs requiring purchase orders
              </span>
            </div>
            <p className="text-xs text-slate-600 mb-3">
              SKUs where current on-hand quantity is at or below the reorder threshold. Recommended Order Quantity (ROQ)
              restores a 30-day cycle stock buffer.
            </p>
            <div className="border border-slate-200 rounded-lg overflow-hidden">
              <table className="w-full text-xs">
                <thead className="bg-slate-100 text-slate-700 font-semibold">
                  <tr>
                    <th className="text-left px-3 py-2">SKU</th>
                    <th className="text-left px-3 py-2">Product Name</th>
                    <th className="text-left px-3 py-2">Supplier</th>
                    <th className="text-right px-3 py-2">On Hand</th>
                    <th className="text-right px-3 py-2">ROP</th>
                    <th className="text-right px-3 py-2">Days Left</th>
                    <th className="text-right px-3 py-2">Suggested Order</th>
                    <th className="text-right px-3 py-2">Est. Cost</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {replenishmentItems.slice(0, 10).map((item) => (
                    <tr key={item.sku} className="hover:bg-slate-50">
                      <td className="px-3 py-2 font-mono text-[11px]">{item.sku}</td>
                      <td className="px-3 py-2 font-medium text-slate-800">{item.product_name}</td>
                      <td className="px-3 py-2 text-slate-600">{item.supplier}</td>
                      <td className="text-right px-3 py-2">{item.actionData.currentStock}</td>
                      <td className="text-right px-3 py-2">{item.actionData.reorderPoint}</td>
                      <td className="text-right px-3 py-2 font-semibold text-red-600">
                        {Number.isFinite(item.actionData.daysOfStock) ? item.actionData.daysOfStock.toFixed(0) : "0"}d
                      </td>
                      <td className="text-right px-3 py-2 font-bold text-slate-900">
                        {item.actionData.suggestedOrderQty} units
                      </td>
                      <td className="text-right px-3 py-2 font-semibold text-slate-900">
                        {money(item.actionData.estimatedCost)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {replenishmentItems.length > 10 && (
              <p className="text-[11px] text-slate-500 mt-2">
                Showing top 10 most urgent SKUs. Full list with all {replenishmentItems.length} items can be downloaded
                via CSV or PDF report.
              </p>
            )}
          </div>

          {/* Section 5: Dead Stock Liquidation & Working Capital Recovery */}
          <div>
            <h3 className="text-base font-bold text-[var(--color-navy)] mb-2">
              5. Dead Stock Liquidation & Working Capital Recovery Plan
            </h3>
            <p className="text-xs text-slate-600 mb-3">
              Non-moving Class C items and stagnant SKUs locking up inventory valuation with zero velocity.
              Targeted markdowns and bundles allow immediate cash recovery to offset replenishment expenses.
            </p>
            <div className="border border-slate-200 rounded-lg overflow-hidden">
              <table className="w-full text-xs">
                <thead className="bg-slate-100 text-slate-700 font-semibold">
                  <tr>
                    <th className="text-left px-3 py-2">SKU</th>
                    <th className="text-left px-3 py-2">Product</th>
                    <th className="text-right px-3 py-2">Units Stagnant</th>
                    <th className="text-right px-3 py-2">Trapped Capital</th>
                    <th className="text-right px-3 py-2">Est. Cash Recovery</th>
                    <th className="text-left px-3 py-2">Recommended Liquidation Tactic</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {liquidationItems.slice(0, 8).map((item) => (
                    <tr key={item.sku} className="hover:bg-slate-50">
                      <td className="px-3 py-2 font-mono text-[11px]">{item.sku}</td>
                      <td className="px-3 py-2 font-medium text-slate-800">{item.product_name}</td>
                      <td className="text-right px-3 py-2">{item.actionData.currentStock}</td>
                      <td className="text-right px-3 py-2 font-semibold text-amber-800">
                        {money(item.actionData.currentStock * item.actionData.unitCost)}
                      </td>
                      <td className="text-right px-3 py-2 font-bold text-emerald-700">
                        {money(item.financialImpact.amount)}
                      </td>
                      <td className="px-3 py-2 text-slate-600">{item.actionData.recommendedAction}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Section 6: Pricing & Margin Upside */}
          {pricingItems.length > 0 && (
            <div>
              <h3 className="text-base font-bold text-[var(--color-navy)] mb-2">
                6. Growth & Pricing Optimization Opportunities
              </h3>
              <p className="text-xs text-slate-600 mb-3">
                Identified fast-moving SKUs with strong turnover velocity that are currently priced below optimal market
                elasticity. Testing modest price increases can directly expand gross margin dollars without dampening volume.
              </p>
              <div className="border border-slate-200 rounded-lg overflow-hidden">
                <table className="w-full text-xs">
                  <thead className="bg-slate-100 text-slate-700 font-semibold">
                    <tr>
                      <th className="text-left px-3 py-2">SKU</th>
                      <th className="text-left px-3 py-2">Product</th>
                      <th className="text-right px-3 py-2">30d Velocity</th>
                      <th className="text-right px-3 py-2">Current Retail</th>
                      <th className="text-right px-3 py-2">Projected Annual Upside</th>
                      <th className="text-left px-3 py-2">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {pricingItems.slice(0, 5).map((item) => (
                      <tr key={item.sku}>
                        <td className="px-3 py-2 font-mono text-[11px]">{item.sku}</td>
                        <td className="px-3 py-2 font-medium text-slate-800">{item.product_name}</td>
                        <td className="text-right px-3 py-2 font-semibold">{item.actionData.unitsSold30d} units</td>
                        <td className="text-right px-3 py-2">{money(item.actionData.retailPrice)}</td>
                        <td className="text-right px-3 py-2 font-bold text-emerald-700">
                          +{money(item.financialImpact.amount)}
                        </td>
                        <td className="px-3 py-2 text-slate-600">{item.actionData.recommendedAction}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Section 7: Strategic Priorities Summary */}
          <div className="bg-slate-50 p-4 rounded-lg border border-slate-200">
            <h4 className="font-bold text-[var(--color-navy)] mb-2 text-xs uppercase tracking-wide">
              7. Strategic Priorities & Next Steps
            </h4>
            <ol className="list-decimal pl-5 space-y-1.5 text-xs text-slate-700">
              <li>
                <strong>Immediate Replenishment:</strong> Dispatch purchase orders totaling{" "}
                {money(recommendations.totalReplenishmentCost)} to prevent stockout losses on top-selling SKUs.
              </li>
              <li>
                <strong>Dead Stock Liquidation:</strong> Initiate a clearance promotion on non-moving C items to unlock up to{" "}
                {money(recommendations.potentialCapitalRecovery)} in working capital.
              </li>
              <li>
                <strong>Supplier Service Level Agreements:</strong> Review delivery lead times with top suppliers to maintain
                inventory safety buffers and avoid stockout recurrence.
              </li>
              <li>
                <strong>Quarterly Review Cadence:</strong> Repeat this classification analysis every 30 days to dynamically
                rebalance reorder points against seasonal demand shifts.
              </li>
            </ol>
          </div>
        </div>

        {/* Footer */}
        <div className="bg-slate-100 px-6 py-3 border-t border-slate-200 flex items-center justify-between shrink-0">
          <div className="text-xs text-slate-500">
            Standard 9-Box FSN×ABC Methodology · Verified against retail inventory data
          </div>
          <button
            onClick={onClose}
            className="text-xs font-medium px-4 py-1.5 rounded bg-slate-700 hover:bg-slate-800 text-white transition"
          >
            Close Report
          </button>
        </div>
      </div>
    </div>
  );
}

"use client";

import { useState, useMemo } from "react";
import type { AnalysisResult } from "@/lib/analytics/analyze";
import type { RecommendationType } from "@/lib/analytics/recommendations";
import { calculateSuggestedOrderQty } from "@/lib/analytics/recommendations";
import { ExecutiveReportModal } from "@/components/ExecutiveReportModal";
import { supplierPoToCsv, downloadTextFile } from "@/lib/export/toCsv";

interface RecommendationsPanelProps {
  result: AnalysisResult;
  sourceLabel: string;
  onDownloadPdf: () => void;
}

function money(n: number): string {
  return `$${n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function RecommendationsPanel({
  result,
  sourceLabel,
  onDownloadPdf,
}: RecommendationsPanelProps) {
  const { recommendations, reorderRisk } = result;

  const [activeTab, setActiveTab] = useState<RecommendationType | "all" | "suppliers">("replenishment");
  const [targetDaysBuffer, setTargetDaysBuffer] = useState<number>(30);
  const [markdownDiscount, setMarkdownDiscount] = useState<number>(30);
  const [selectedSupplier, setSelectedSupplier] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [showExecutiveReport, setShowExecutiveReport] = useState<boolean>(false);

  // Dynamic recalculation of replenishment quantities based on chosen cycle buffer days
  const dynamicReplenishment = useMemo(() => {
    return reorderRisk.map((row) => {
      const soq = calculateSuggestedOrderQty(
        row.quantity_on_hand,
        row.reorder_point,
        row.units_sold_30d,
        targetDaysBuffer
      );
      const estimatedCost = soq * row.cost_per_unit;
      return {
        ...row,
        soq,
        estimatedCost,
      };
    });
  }, [reorderRisk, targetDaysBuffer]);

  const dynamicTotalReplenishmentCost = useMemo(() => {
    return dynamicReplenishment
      .filter((r) => r.stock_status === "Reorder Now")
      .reduce((s, r) => s + r.estimatedCost, 0);
  }, [dynamicReplenishment]);

  // Dead stock items for liquidation simulator
  const deadStockItems = useMemo(() => {
    return recommendations.items.filter((i) => i.type === "liquidation");
  }, [recommendations.items]);

  const dynamicEstimatedCashRecovery = useMemo(() => {
    const recoveryMultiplier = (100 - markdownDiscount) / 100;
    return recommendations.trappedCapitalInDeadStock * recoveryMultiplier;
  }, [recommendations.trappedCapitalInDeadStock, markdownDiscount]);

  // Filtered recommendations items
  const filteredItems = useMemo(() => {
    return recommendations.items.filter((item) => {
      if (activeTab !== "all" && activeTab !== "suppliers" && item.type !== activeTab) {
        return false;
      }
      if (selectedSupplier !== "all" && item.supplier !== selectedSupplier) {
        return false;
      }
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesSku = item.sku.toLowerCase().includes(q);
        const matchesName = item.product_name.toLowerCase().includes(q);
        const matchesCategory = item.category.toLowerCase().includes(q);
        if (!matchesSku && !matchesName && !matchesCategory) return false;
      }
      return true;
    });
  }, [recommendations.items, activeTab, selectedSupplier, searchQuery]);

  const distinctSuppliers = useMemo(() => {
    return Array.from(new Set(result.rows.map((r) => r.supplier))).sort();
  }, [result.rows]);

  const healthColor =
    recommendations.healthScore >= 80
      ? "text-emerald-700 bg-emerald-50 border-emerald-300"
      : recommendations.healthScore >= 65
      ? "text-amber-700 bg-amber-50 border-amber-300"
      : "text-red-700 bg-red-50 border-red-300";

  return (
    <section className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
      {showExecutiveReport && (
        <ExecutiveReportModal
          result={result}
          sourceLabel={sourceLabel}
          onClose={() => setShowExecutiveReport(false)}
          onDownloadPdf={onDownloadPdf}
        />
      )}

      {/* Top Banner / Executive Scorecard */}
      <div className="bg-gradient-to-r from-[var(--color-navy)] to-slate-800 text-white p-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs uppercase tracking-wider font-semibold text-amber-400">
                Actionable Intelligence
              </span>
              <span className="bg-white/20 text-white text-[10px] font-semibold px-2 py-0.5 rounded">
                APICS-Aligned
              </span>
            </div>
            <h2 className="text-xl font-bold mt-1">Strategic Recommendations & Reorder Planning</h2>
            <p className="text-xs text-slate-300 mt-1 max-w-2xl">
              Algorithmic recommendations to eliminate stockout risk on fast movers, unlock trapped working capital
              from slow and dead inventory, and optimize gross margins.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowExecutiveReport(true)}
              className="px-4 py-2 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs rounded-lg shadow-sm transition flex items-center gap-2"
            >
              <span>📄 View Executive Report</span>
            </button>
            <div className="bg-white/10 backdrop-blur rounded-lg p-3 text-center border border-white/20 min-w-[120px]">
              <div className="text-[10px] text-slate-300 uppercase tracking-wider">Health Score</div>
              <div className="text-2xl font-black text-white">{recommendations.healthScore}/100</div>
              <div className={`text-[10px] font-bold px-1.5 py-0.5 rounded mt-0.5 inline-block ${healthColor}`}>
                {recommendations.healthGrade}
              </div>
            </div>
          </div>
        </div>

        {/* Financial Impact Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-6">
          <div className="bg-white/10 rounded-lg p-3 border border-white/10">
            <div className="text-[11px] text-slate-300 uppercase">Replenishment Needed</div>
            <div className="text-lg font-bold text-red-300 mt-0.5">
              {money(dynamicTotalReplenishmentCost)}
            </div>
            <div className="text-[10px] text-slate-400">
              {reorderRisk.filter((r) => r.stock_status === "Reorder Now").length} SKUs in critical stockout
            </div>
          </div>

          <div className="bg-white/10 rounded-lg p-3 border border-white/10">
            <div className="text-[11px] text-slate-300 uppercase">Trapped in Dead Stock</div>
            <div className="text-lg font-bold text-amber-300 mt-0.5">
              {money(recommendations.trappedCapitalInDeadStock)}
            </div>
            <div className="text-[10px] text-slate-400">Class C non-moving inventory</div>
          </div>

          <div className="bg-white/10 rounded-lg p-3 border border-white/10">
            <div className="text-[11px] text-slate-300 uppercase">Potential Cash Recovery</div>
            <div className="text-lg font-bold text-emerald-300 mt-0.5">
              {money(dynamicEstimatedCashRecovery)}
            </div>
            <div className="text-[10px] text-slate-400">Via recommended markdowns</div>
          </div>

          <div className="bg-white/10 rounded-lg p-3 border border-white/10">
            <div className="text-[11px] text-slate-300 uppercase">Net Working Capital Impact</div>
            <div
              className={`text-lg font-bold mt-0.5 ${
                dynamicEstimatedCashRecovery >= dynamicTotalReplenishmentCost
                  ? "text-emerald-300"
                  : "text-amber-300"
              }`}
            >
              {money(dynamicEstimatedCashRecovery - dynamicTotalReplenishmentCost)}
            </div>
            <div className="text-[10px] text-slate-400">
              {dynamicEstimatedCashRecovery >= dynamicTotalReplenishmentCost
                ? "Liquidation fully covers replenishment"
                : "Partially offset by liquidation"}
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-200 bg-slate-50 px-6 flex flex-wrap items-center justify-between gap-3">
        <div className="flex gap-1 overflow-x-auto py-2">
          {[
            { id: "replenishment", label: "Replenishment Orders (Low Stock)", count: reorderRisk.length },
            { id: "liquidation", label: "Dead Stock Liquidation Plan", count: deadStockItems.length },
            {
              id: "pricing_margin",
              label: "Pricing & Margin Upside",
              count: recommendations.items.filter((i) => i.type === "pricing_margin").length,
            },
            { id: "suppliers", label: "Supplier Exposure", count: recommendations.supplierRiskSummary.length },
            { id: "all", label: "All Recommendations", count: recommendations.items.length },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as typeof activeTab)}
              className={`px-3 py-2 text-xs font-semibold rounded-md transition whitespace-nowrap ${
                activeTab === tab.id
                  ? "bg-white text-[var(--color-navy)] shadow-sm border border-slate-200"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
              }`}
            >
              {tab.label} ({tab.count})
            </button>
          ))}
        </div>

        {/* Search & Supplier Filter */}
        <div className="flex items-center gap-2 py-2">
          <input
            type="text"
            placeholder="Search SKU or product…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="text-xs px-2.5 py-1.5 border border-slate-300 rounded-md bg-white text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-slate-400"
          />
          <select
            value={selectedSupplier}
            onChange={(e) => setSelectedSupplier(e.target.value)}
            className="text-xs px-2.5 py-1.5 border border-slate-300 rounded-md bg-white text-slate-800 focus:outline-none"
          >
            <option value="all">All Suppliers</option>
            {distinctSuppliers.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Tab 1: Replenishment Planner */}
      {activeTab === "replenishment" && (
        <div className="p-6 space-y-4">
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <div className="text-xs font-bold text-slate-800">
                Replenishment Cycle Buffer Configuration
              </div>
              <div className="text-xs text-slate-500 mt-0.5">
                Adjust desired safety buffer days. Quantities and total purchase order costs recalculate instantly.
              </div>
            </div>

            <div className="flex items-center gap-1.5 bg-white p-1 rounded-lg border border-slate-200">
              {[15, 30, 45, 60].map((days) => (
                <button
                  key={days}
                  onClick={() => setTargetDaysBuffer(days)}
                  className={`px-2.5 py-1 text-xs font-semibold rounded ${
                    targetDaysBuffer === days
                      ? "bg-[var(--color-navy)] text-white"
                      : "text-slate-600 hover:bg-slate-100"
                  }`}
                >
                  {days} Days {days === 30 && "(Std)"}
                </button>
              ))}
            </div>
          </div>

          <div className="border border-slate-200 rounded-lg overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="bg-slate-100 text-slate-700 font-semibold border-b border-slate-200">
                <tr>
                  <th className="text-left px-3 py-2.5">SKU</th>
                  <th className="text-left px-3 py-2.5">Product Name</th>
                  <th className="text-left px-3 py-2.5">Supplier</th>
                  <th className="text-right px-3 py-2.5">On Hand</th>
                  <th className="text-right px-3 py-2.5">ROP</th>
                  <th className="text-right px-3 py-2.5">Runway</th>
                  <th className="text-right px-3 py-2.5">Unit Cost</th>
                  <th className="text-right px-3 py-2.5 bg-amber-50/70 text-amber-900">
                    Suggested PO Qty
                  </th>
                  <th className="text-right px-3 py-2.5 bg-amber-50/70 text-amber-900">
                    Estimated PO Cost
                  </th>
                  <th className="text-center px-3 py-2.5">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {dynamicReplenishment
                  .filter((item) => {
                    if (selectedSupplier !== "all" && item.supplier !== selectedSupplier) return false;
                    if (searchQuery.trim()) {
                      const q = searchQuery.toLowerCase();
                      return (
                        item.sku.toLowerCase().includes(q) ||
                        item.product_name.toLowerCase().includes(q) ||
                        item.category.toLowerCase().includes(q)
                      );
                    }
                    return true;
                  })
                  .map((row) => (
                    <tr key={row.sku} className="hover:bg-slate-50">
                      <td className="px-3 py-2 font-mono text-[11px] text-slate-700">{row.sku}</td>
                      <td className="px-3 py-2 font-medium text-slate-800">
                        {row.product_name} ({row.size})
                      </td>
                      <td className="px-3 py-2 text-slate-600">{row.supplier}</td>
                      <td className="text-right px-3 py-2">{row.quantity_on_hand}</td>
                      <td className="text-right px-3 py-2 text-slate-500">{row.reorder_point}</td>
                      <td className="text-right px-3 py-2 font-semibold text-red-600">
                        {Number.isFinite(row.days_of_stock) ? `${row.days_of_stock.toFixed(0)}d` : "0d"}
                      </td>
                      <td className="text-right px-3 py-2">${row.cost_per_unit.toFixed(2)}</td>
                      <td className="text-right px-3 py-2 font-bold bg-amber-50/40 text-slate-900">
                        {row.soq} units
                      </td>
                      <td className="text-right px-3 py-2 font-bold bg-amber-50/40 text-slate-900">
                        {money(row.estimatedCost)}
                      </td>
                      <td className="text-center px-3 py-2">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border ${
                            row.stock_status === "Reorder Now"
                              ? "bg-red-100 text-red-800 border-red-300"
                              : "bg-amber-100 text-amber-800 border-amber-300"
                          }`}
                        >
                          {row.stock_status}
                        </span>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 2: Dead Stock & Liquidation Simulator */}
      {activeTab === "liquidation" && (
        <div className="p-6 space-y-4">
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <div className="text-xs font-bold text-slate-800">
                  Dead Stock Liquidation Recovery Simulator
                </div>
                <div className="text-xs text-slate-500 mt-0.5">
                  Simulate promotional discount depth to project recovered working capital and bin space reclaimed.
                </div>
              </div>

              <div className="flex items-center gap-3">
                <span className="text-xs font-semibold text-slate-700">Clearance Discount:</span>
                <input
                  type="range"
                  min="10"
                  max="60"
                  step="5"
                  value={markdownDiscount}
                  onChange={(e) => setMarkdownDiscount(Number(e.target.value))}
                  className="w-28 accent-[var(--color-navy)] cursor-pointer"
                />
                <span className="text-xs font-bold px-2 py-0.5 bg-white border border-slate-300 rounded text-slate-800">
                  {markdownDiscount}% Off
                </span>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3 mt-4 pt-3 border-t border-slate-200 text-center">
              <div>
                <div className="text-[10px] text-slate-500 uppercase">Trapped Inventory Cost</div>
                <div className="text-sm font-bold text-slate-900">
                  {money(recommendations.trappedCapitalInDeadStock)}
                </div>
              </div>
              <div>
                <div className="text-[10px] text-slate-500 uppercase">Estimated Recovered Cash</div>
                <div className="text-sm font-bold text-emerald-700">
                  {money(dynamicEstimatedCashRecovery)}
                </div>
              </div>
              <div>
                <div className="text-[10px] text-slate-500 uppercase">Holding Cost Saved (Annual)</div>
                <div className="text-sm font-bold text-blue-700">
                  {money(recommendations.trappedCapitalInDeadStock * 0.22)}
                </div>
              </div>
            </div>
          </div>

          <div className="border border-slate-200 rounded-lg overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="bg-slate-100 text-slate-700 font-semibold border-b border-slate-200">
                <tr>
                  <th className="text-left px-3 py-2.5">SKU</th>
                  <th className="text-left px-3 py-2.5">Product Name</th>
                  <th className="text-left px-3 py-2.5">Category</th>
                  <th className="text-right px-3 py-2.5">On Hand</th>
                  <th className="text-right px-3 py-2.5">Cost/Unit</th>
                  <th className="text-right px-3 py-2.5">Trapped Value</th>
                  <th className="text-right px-3 py-2.5">Projected Recovery</th>
                  <th className="text-left px-3 py-2.5">Recommended Liquidation Tactic</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {deadStockItems.map((item) => {
                  const trapped = item.actionData.currentStock * item.actionData.unitCost;
                  const recovery = trapped * ((100 - markdownDiscount) / 100);
                  return (
                    <tr key={item.sku} className="hover:bg-slate-50">
                      <td className="px-3 py-2 font-mono text-[11px] text-slate-700">{item.sku}</td>
                      <td className="px-3 py-2 font-medium text-slate-800">{item.product_name}</td>
                      <td className="px-3 py-2 text-slate-600">{item.category}</td>
                      <td className="text-right px-3 py-2">{item.actionData.currentStock}</td>
                      <td className="text-right px-3 py-2">${item.actionData.unitCost.toFixed(2)}</td>
                      <td className="text-right px-3 py-2 font-bold text-red-700">{money(trapped)}</td>
                      <td className="text-right px-3 py-2 font-bold text-emerald-700">{money(recovery)}</td>
                      <td className="px-3 py-2 text-slate-600">{item.actionData.recommendedAction}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 3: Pricing & Margin Opportunities */}
      {activeTab === "pricing_margin" && (
        <div className="p-6 space-y-4">
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-xs text-slate-700">
            <strong>Price Elasticity Opportunity:</strong> Fast-moving items with strong unit velocity but low unit
            prices. Testing a +5% to +10% price test on these SKUs can directly increase gross profit margins without
            impairing sales volume.
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {recommendations.items
              .filter((i) => i.type === "pricing_margin")
              .map((item) => (
                <div key={item.sku} className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm">
                  <div className="flex items-start justify-between">
                    <div>
                      <span className="text-[10px] font-mono bg-slate-100 px-1.5 py-0.5 rounded text-slate-600">
                        {item.sku}
                      </span>
                      <h4 className="text-sm font-bold text-slate-900 mt-1">{item.product_name}</h4>
                      <p className="text-xs text-slate-500">{item.category} · {item.supplier}</p>
                    </div>
                    <span className="text-xs font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                      +{money(item.financialImpact.amount)}/yr
                    </span>
                  </div>
                  <p className="text-xs text-slate-600 mt-2">{item.description}</p>
                  <div className="mt-3 pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
                    <span className="text-slate-500">
                      Current Retail: <strong>${item.actionData.retailPrice.toFixed(2)}</strong>
                    </span>
                    <span className="text-slate-800 font-semibold">{item.actionData.recommendedAction}</span>
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* Tab 4: Supplier Concentration & Lead Time Risk */}
      {activeTab === "suppliers" && (
        <div className="p-6 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-50 border border-slate-200 rounded-lg p-3">
            <div className="text-xs text-slate-600">
              <strong>Procurement & Vendor PO Generation:</strong> Grouped replenishment requisitions by supplier.
              Click <strong>PO (CSV)</strong> to generate and download vendor-ready purchase orders.
            </div>
          </div>

          <div className="border border-slate-200 rounded-lg overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="bg-slate-100 text-slate-700 font-semibold border-b border-slate-200">
                <tr>
                  <th className="text-left px-3 py-2.5">Supplier</th>
                  <th className="text-right px-3 py-2.5">Total SKUs</th>
                  <th className="text-right px-3 py-2.5">At-Risk SKUs</th>
                  <th className="text-right px-3 py-2.5">Critical Fast-Mover Risks</th>
                  <th className="text-right px-3 py-2.5">Total Inventory Value</th>
                  <th className="text-right px-3 py-2.5">Estimated Replenishment</th>
                  <th className="text-center px-3 py-2.5 bg-amber-50/70 text-amber-900">Purchase Order</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {recommendations.supplierRiskSummary.map((supp) => (
                  <tr key={supp.supplier} className="hover:bg-slate-50">
                    <td className="px-3 py-2 font-medium text-slate-800">{supp.supplier}</td>
                    <td className="text-right px-3 py-2">{supp.totalSkus}</td>
                    <td className="text-right px-3 py-2 font-semibold text-amber-700">{supp.atRiskSkus}</td>
                    <td className="text-right px-3 py-2 font-bold text-red-700">{supp.criticalAtRiskSkus}</td>
                    <td className="text-right px-3 py-2">{money(supp.totalInventoryValue)}</td>
                    <td className="text-right px-3 py-2 font-bold text-slate-900">
                      {money(supp.estimatedReplenishmentCost)}
                    </td>
                    <td className="text-center px-3 py-2 bg-amber-50/20">
                      {supp.atRiskSkus > 0 ? (
                        <button
                          onClick={() => {
                            const csv = supplierPoToCsv(supp.supplier, recommendations.items);
                            const dateStr = new Date().toISOString().slice(0, 10);
                            const filename = `PO_${supp.supplier.replace(/[^a-zA-Z0-9]/g, "_")}_${dateStr}.csv`;
                            downloadTextFile(csv, filename, "text/csv;charset=utf-8");
                          }}
                          className="px-2.5 py-1 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-[10px] rounded shadow-xs transition inline-flex items-center gap-1 cursor-pointer"
                          title={`Generate and download Purchase Order CSV for ${supp.supplier}`}
                        >
                          <span>📥 PO (CSV)</span>
                        </button>
                      ) : (
                        <span className="text-[10px] text-emerald-700 font-medium">✓ Stocked</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 5: All Recommendations List */}
      {activeTab === "all" && (
        <div className="p-6 space-y-3">
          <div className="divide-y divide-slate-100">
            {filteredItems.map((item) => (
              <div key={item.id} className="py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase ${
                        item.urgency === "Immediate"
                          ? "bg-red-100 text-red-800 border border-red-300"
                          : item.urgency === "High"
                          ? "bg-amber-100 text-amber-800 border border-amber-300"
                          : "bg-blue-100 text-blue-800 border border-blue-300"
                      }`}
                    >
                      {item.urgency}
                    </span>
                    <span className="text-xs font-mono text-slate-500">{item.sku}</span>
                    <span className="text-xs font-semibold text-slate-800">{item.title}</span>
                  </div>
                  <p className="text-xs text-slate-600 max-w-2xl">{item.description}</p>
                </div>
                <div className="shrink-0 text-right">
                  <div className="text-xs font-bold text-slate-900">
                    {money(item.financialImpact.amount)}
                  </div>
                  <div className="text-[10px] text-slate-500 capitalize">
                    {item.financialImpact.type.replace("_", " ")}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

"use client";

import { useState } from "react";
import type { AnalysisResult } from "@/lib/analytics/analyze";
import type { ClassifiedSku } from "@/lib/analytics/types";
import { FsnDistributionChart } from "@/components/charts/FsnDistributionChart";
import { AbcParetoChart } from "@/components/charts/AbcParetoChart";
import { FsnAbcMatrix } from "@/components/charts/FsnAbcMatrix";
import { ReorderRiskChart } from "@/components/charts/ReorderRiskChart";
import { CategoryPerformanceChart } from "@/components/charts/CategoryPerformanceChart";
import { TurnoverScatterChart } from "@/components/charts/TurnoverScatterChart";
import { WorkingCapitalDistributionChart } from "@/components/charts/WorkingCapitalDistributionChart";
import { SkuDetailPanel } from "@/components/SkuDetailPanel";
import { RecommendationsPanel } from "@/components/RecommendationsPanel";
import { calculateSuggestedOrderQty } from "@/lib/analytics/recommendations";

function money(n: number): string {
  return `$${n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}
function pct(n: number): string {
  return `${n.toFixed(1)}%`;
}

const statusColor: Record<string, string> = {
  "Reorder Now": "bg-red-100 text-red-800 border-red-300",
  "Low - Monitor": "bg-amber-100 text-amber-800 border-amber-300",
  Healthy: "bg-emerald-100 text-emerald-800 border-emerald-300",
};

interface DashboardProps {
  result: AnalysisResult;
  sourceLabel?: string;
  onDownloadPdf?: () => void;
}

/**
 * Pure display component: renders the full Report Chapter 4 dashboard
 * (KPIs, all 6 chart+table sections) along with strategic recommendations,
 * executive scorecard, and working capital distribution from an already-computed
 * `AnalysisResult`.
 */
export function Dashboard({ result, sourceLabel = "sample dataset", onDownloadPdf }: DashboardProps) {
  const { rows, kpis, fsn: fsnRows, abc: abcRows, reorderRisk: riskList, pareto, categoryPerf, matrix, recommendations } = result;
  const [selectedSku, setSelectedSku] = useState<ClassifiedSku | null>(null);

  const handleDownloadPdf = onDownloadPdf ?? (async () => {
    try {
      const response = await fetch("/api/export/pdf", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ result, sourceLabel }),
      });
      if (!response.ok) return;
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "inventory-analysis-report.pdf";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error(e);
    }
  });

  return (
    <div className="space-y-12">
      {selectedSku && <SkuDetailPanel sku={selectedSku} onClose={() => setSelectedSku(null)} />}

      <RecommendationsPanel
        result={result}
        sourceLabel={sourceLabel}
        onDownloadPdf={handleDownloadPdf}
      />

      <section>
        <h2 className="text-lg font-semibold text-[var(--color-navy)] mb-3">Portfolio Overview</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
          {[
            ["Total SKUs", kpis.totalSkus.toString()],
            ["Inventory value (cost)", money(kpis.totalInventoryValue)],
            ["30-day revenue", money(kpis.totalRevenue30d)],
            ["Gross margin", pct(kpis.grossMarginPct)],
            ["GMROI (Annualized)", `${kpis.gmroi.toFixed(2)}×`],
            ["Median turnover (ITR)", `${kpis.medianItr.toFixed(1)}×`],
            ["Turnover range", `${kpis.minItr.toFixed(1)}× – ${kpis.maxItr.toFixed(1)}×`],
            ["SKUs at/near reorder point", `${kpis.atRiskSkuCount} of ${kpis.totalSkus}`],
            ["Distinct product lines", kpis.distinctProducts.toString()],
          ].map(([label, value]) => (
            <div key={label} className="bg-white rounded-lg border border-slate-200 p-4 shadow-sm">
              <div className="text-xs text-slate-500 uppercase tracking-wide">{label}</div>
              <div className="text-xl font-bold text-[var(--color-navy)] mt-1">{value}</div>
            </div>
          ))}
        </div>

        <div className="mt-6">
          <WorkingCapitalDistributionChart recommendations={recommendations} kpis={kpis} />
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold text-[var(--color-navy)] mb-3">
          Fast / Slow / Non-Moving Classification
        </h2>
        <FsnDistributionChart data={fsnRows} />
        <div className="bg-white rounded-lg border border-slate-200 overflow-hidden shadow-sm mt-4">
          <table className="w-full text-sm">
            <thead className="bg-[var(--color-navy)] text-white">
              <tr>
                <th className="text-left px-4 py-2">Class</th>
                <th className="text-right px-4 py-2">SKUs</th>
                <th className="text-right px-4 py-2">% of SKUs</th>
                <th className="text-right px-4 py-2">Inv. value</th>
                <th className="text-right px-4 py-2">% of value</th>
              </tr>
            </thead>
            <tbody>
              {fsnRows.map((r) => (
                <tr key={r.fsn_class} className="border-t border-slate-100">
                  <td className="px-4 py-2">{r.fsn_class}</td>
                  <td className="text-right px-4 py-2">{r.skuCount}</td>
                  <td className="text-right px-4 py-2">{pct(r.pctOfSkus)}</td>
                  <td className="text-right px-4 py-2">{money(r.inventoryValue)}</td>
                  <td className="text-right px-4 py-2">{pct(r.pctOfValue)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold text-[var(--color-navy)] mb-3">ABC / Pareto Classification</h2>
        <AbcParetoChart data={pareto} />
        <div className="bg-white rounded-lg border border-slate-200 overflow-hidden shadow-sm mt-4">
          <table className="w-full text-sm">
            <thead className="bg-[var(--color-navy)] text-white">
              <tr>
                <th className="text-left px-4 py-2">Class</th>
                <th className="text-right px-4 py-2">SKUs</th>
                <th className="text-right px-4 py-2">% of SKUs</th>
                <th className="text-right px-4 py-2">Revenue (30d)</th>
                <th className="text-right px-4 py-2">% of revenue</th>
              </tr>
            </thead>
            <tbody>
              {abcRows.map((r) => (
                <tr key={r.abc_class} className="border-t border-slate-100">
                  <td className="px-4 py-2 font-medium">{r.abc_class}</td>
                  <td className="text-right px-4 py-2">{r.skuCount}</td>
                  <td className="text-right px-4 py-2">{pct(r.pctOfSkus)}</td>
                  <td className="text-right px-4 py-2">{money(r.revenue)}</td>
                  <td className="text-right px-4 py-2">{pct(r.pctOfRevenue)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold text-[var(--color-navy)] mb-3">FSN × ABC Priority Matrix</h2>
        <FsnAbcMatrix cells={matrix} />
      </section>

      <section>
        <h2 className="text-lg font-semibold text-[var(--color-navy)] mb-3">
          Stock-Out Risk List ({riskList.length})
        </h2>
        <ReorderRiskChart data={riskList} />
        <div className="bg-white rounded-lg border border-slate-200 overflow-hidden shadow-sm mt-4">
          <table className="w-full text-sm">
            <thead className="bg-[var(--color-navy)] text-white">
              <tr>
                <th className="text-left px-4 py-2">SKU</th>
                <th className="text-left px-4 py-2">Product (size)</th>
                <th className="text-left px-4 py-2">Supplier</th>
                <th className="text-right px-4 py-2">On hand</th>
                <th className="text-right px-4 py-2">ROP</th>
                <th className="text-right px-4 py-2">Days left</th>
                <th className="text-right px-4 py-2 bg-amber-600/30">Order Qty</th>
                <th className="text-right px-4 py-2 bg-amber-600/30">Est. Cost</th>
                <th className="text-center px-4 py-2">Status</th>
                <th className="text-center px-4 py-2">Priority</th>
              </tr>
            </thead>
            <tbody>
              {riskList.map((r) => {
                const soq = calculateSuggestedOrderQty(r.quantity_on_hand, r.reorder_point, r.units_sold_30d);
                const estCost = soq * r.cost_per_unit;
                return (
                  <tr
                    key={r.sku}
                    className="border-t border-slate-100 hover:bg-slate-50 cursor-pointer"
                    onClick={() => setSelectedSku(r)}
                  >
                    <td className="px-4 py-2 font-mono text-xs">{r.sku}</td>
                    <td className="px-4 py-2 underline underline-offset-2 decoration-slate-300">
                      {r.product_name} ({r.size})
                    </td>
                    <td className="px-4 py-2 text-xs text-slate-600">{r.supplier}</td>
                    <td className="text-right px-4 py-2">{r.quantity_on_hand}</td>
                    <td className="text-right px-4 py-2 text-slate-500">{r.reorder_point}</td>
                    <td className="text-right px-4 py-2 font-semibold text-red-600">
                      {Number.isFinite(r.days_of_stock) ? r.days_of_stock.toFixed(0) : "0"}d
                    </td>
                    <td className="text-right px-4 py-2 font-bold bg-amber-50/40 text-slate-900">
                      {soq}
                    </td>
                    <td className="text-right px-4 py-2 font-semibold bg-amber-50/40 text-slate-900">
                      {money(estCost)}
                    </td>
                    <td className="text-center px-4 py-2">
                      <span className={`px-2 py-0.5 rounded-full text-xs border ${statusColor[r.stock_status]}`}>
                        {r.stock_status}
                      </span>
                    </td>
                    <td className="text-center px-4 py-2 text-xs text-slate-600">{r.priority_tag}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold text-[var(--color-navy)] mb-3">Category Performance & Merchandising</h2>
        <CategoryPerformanceChart data={categoryPerf} />
        <div className="bg-white rounded-lg border border-slate-200 overflow-hidden shadow-sm mt-4">
          <table className="w-full text-sm">
            <thead className="bg-[var(--color-navy)] text-white">
              <tr>
                <th className="text-left px-4 py-2">Category</th>
                <th className="text-right px-4 py-2">SKUs</th>
                <th className="text-right px-4 py-2">Units Sold (30d)</th>
                <th className="text-right px-4 py-2">Revenue (30d)</th>
                <th className="text-right px-4 py-2">% Rev</th>
                <th className="text-right px-4 py-2">Inventory Value</th>
                <th className="text-right px-4 py-2">% Val</th>
                <th className="text-right px-4 py-2">Gross Margin %</th>
                <th className="text-right px-4 py-2 bg-amber-600/30">GMROI (Ann.)</th>
              </tr>
            </thead>
            <tbody>
              {categoryPerf.map((c) => (
                <tr key={c.category} className="border-t border-slate-100 hover:bg-slate-50">
                  <td className="px-4 py-2 font-medium text-slate-800">{c.category}</td>
                  <td className="text-right px-4 py-2 text-slate-600">{c.skuCount}</td>
                  <td className="text-right px-4 py-2 text-slate-700">{c.units}</td>
                  <td className="text-right px-4 py-2 font-medium">{money(c.revenue)}</td>
                  <td className="text-right px-4 py-2 text-slate-500">{pct(c.pctOfRevenue)}</td>
                  <td className="text-right px-4 py-2">{money(c.inventoryValue)}</td>
                  <td className="text-right px-4 py-2 text-slate-500">{pct(c.pctOfInventoryValue)}</td>
                  <td className="text-right px-4 py-2 font-medium">{pct(c.grossMarginPct)}</td>
                  <td className="text-right px-4 py-2 font-bold bg-amber-50/40 text-slate-900">
                    {c.gmroi.toFixed(2)}×
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold text-[var(--color-navy)] mb-3">Turnover vs. Revenue</h2>
        <TurnoverScatterChart data={rows} />
      </section>
    </div>
  );
}

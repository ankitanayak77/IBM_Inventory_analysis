"use client";

import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend,
  type TooltipValueType,
} from "recharts";
import type { InventoryRecommendationsSummary } from "@/lib/analytics/recommendations";
import type { PortfolioKpis } from "@/lib/analytics/summary";

interface WorkingCapitalDistributionChartProps {
  recommendations: InventoryRecommendationsSummary;
  kpis: PortfolioKpis;
}

function money(n: number): string {
  return `$${n.toLocaleString("en-US", { maximumFractionDigits: 0 })}`;
}

export function WorkingCapitalDistributionChart({
  recommendations,
  kpis,
}: WorkingCapitalDistributionChartProps) {
  const totalValue = kpis.totalInventoryValue;
  const deadCapital = recommendations.trappedCapitalInDeadStock;
  const slowCapital = Math.max(0, recommendations.trappedCapitalInSlowMoving - deadCapital);
  const replenishmentNeeded = recommendations.totalReplenishmentCost;
  const productiveCapital = Math.max(0, totalValue - slowCapital - deadCapital);

  const data = [
    {
      name: "Productive / Fast Active Capital",
      value: Math.round(productiveCapital),
      color: "#2E7D32", // Green
      description: "Healthy inventory actively generating revenue",
    },
    {
      name: "Slow-Moving Working Capital",
      value: Math.round(slowCapital),
      color: "#E0932A", // Amber
      description: "Capital turning slowly; requires sales promotions",
    },
    {
      name: "Frozen / Dead Stock Capital",
      value: Math.round(deadCapital),
      color: "#C0392B", // Red
      description: "Non-moving stock; target for liquidation markdowns",
    },
  ];

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4 shadow-sm">
      <div className="flex items-center justify-between mb-2">
        <div className="text-sm font-medium text-slate-700">Working Capital Distribution</div>
        <div className="text-xs text-slate-500">
          Total Valuation: <span className="font-semibold text-slate-700">{money(totalValue)}</span>
        </div>
      </div>
      <p className="text-xs text-slate-500 mb-4">
        Breakdown of capital deployed in active vs slow vs frozen inventory tiers.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-center">
        <ResponsiveContainer width="100%" height={220}>
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={55}
              outerRadius={85}
              paddingAngle={3}
              dataKey="value"
            >
              {data.map((entry) => (
                <Cell key={entry.name} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value: TooltipValueType | undefined) => [
                `${money(Number(value))} (${totalValue > 0 ? ((Number(value) / totalValue) * 100).toFixed(1) : 0}%)`,
                "Capital",
              ]}
            />
            <Legend
              verticalAlign="bottom"
              wrapperStyle={{ fontSize: "11px", paddingTop: "8px" }}
            />
          </PieChart>
        </ResponsiveContainer>

        <div className="space-y-3">
          {data.map((item) => {
            const share = totalValue > 0 ? (item.value / totalValue) * 100 : 0;
            return (
              <div key={item.name} className="border-l-4 pl-3 py-1" style={{ borderColor: item.color }}>
                <div className="flex justify-between items-baseline text-xs">
                  <span className="font-medium text-slate-800">{item.name}</span>
                  <span className="font-bold text-slate-900">
                    {money(item.value)} ({share.toFixed(1)}%)
                  </span>
                </div>
                <div className="text-[11px] text-slate-500 mt-0.5">{item.description}</div>
              </div>
            );
          })}

          <div className="bg-slate-50 rounded p-2.5 border border-slate-200 mt-2">
            <div className="text-[11px] font-semibold text-slate-700 mb-0.5">
              Replenishment Capital Requirement:
            </div>
            <div className="text-xs text-slate-600">
              <span className="font-bold text-red-700">{money(replenishmentNeeded)}</span> needed immediately
              to restore target buffers for stockout-critical SKUs.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

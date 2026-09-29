"use client";

import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  type TooltipValueType,
} from "recharts";
import type { ProductParetoRow } from "@/lib/analytics/summary";

function money(n: number): string {
  return `$${n.toLocaleString("en-US", { maximumFractionDigits: 0 })}`;
}

/** Report Figure 2 — revenue by product line with cumulative-% Pareto curve. */
export function AbcParetoChart({ data }: { data: ProductParetoRow[] }) {
  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4 shadow-sm">
      <div className="text-sm font-medium text-slate-600 mb-2">
        Revenue concentration by product line — dashed line marks the 80% A-class cut-off
      </div>
      <ResponsiveContainer width="100%" height={340}>
        <ComposedChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 70 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
          <XAxis
            dataKey="product_name"
            tick={{ fontSize: 10 }}
            angle={-45}
            textAnchor="end"
            interval={0}
            height={80}
          />
          <YAxis
            yAxisId="revenue"
            tick={{ fontSize: 11 }}
            tickFormatter={money}
            label={{ value: "Revenue (30d)", angle: -90, position: "insideLeft", fontSize: 11 }}
          />
          <YAxis
            yAxisId="cumPct"
            orientation="right"
            domain={[0, 110]}
            tick={{ fontSize: 11 }}
            tickFormatter={(v: number) => `${v}%`}
          />
          <Tooltip
            formatter={(value: TooltipValueType | undefined, name: string | number | undefined) =>
              name === "cumulativePct" ? [`${Number(value).toFixed(1)}%`, "Cumulative %"] : [money(Number(value)), "Revenue"]
            }
          />
          <ReferenceLine yAxisId="cumPct" y={80} stroke="#C0392B" strokeDasharray="4 4" />
          <Bar yAxisId="revenue" dataKey="revenue" fill="#0F1F3D" radius={[3, 3, 0, 0]} />
          <Line
            yAxisId="cumPct"
            type="monotone"
            dataKey="cumulativePct"
            stroke="#D4973A"
            strokeWidth={2.5}
            dot={{ r: 3, fill: "#D4973A" }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

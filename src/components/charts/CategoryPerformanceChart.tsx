"use client";

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, type TooltipValueType } from "recharts";
import type { CategoryPerformanceRow } from "@/lib/analytics/summary";

function money(n: number): string {
  return `$${n.toLocaleString("en-US", { maximumFractionDigits: 0 })}`;
}

/** Report Figure 5 — units sold vs. revenue generated, by category. */
export function CategoryPerformanceChart({ data }: { data: CategoryPerformanceRow[] }) {
  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4 shadow-sm">
      <div className="text-sm font-medium text-slate-600 mb-2">Units moved vs. revenue generated, by category</div>
      <ResponsiveContainer width="100%" height={320}>
        <BarChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 30 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
          <XAxis dataKey="category" tick={{ fontSize: 11 }} angle={-15} textAnchor="end" height={50} />
          <YAxis
            yAxisId="units"
            tick={{ fontSize: 11 }}
            label={{ value: "Units sold (30d)", angle: -90, position: "insideLeft", fontSize: 11 }}
          />
          <YAxis yAxisId="revenue" orientation="right" tick={{ fontSize: 11 }} tickFormatter={money} />
          <Tooltip
            formatter={(value: TooltipValueType | undefined, name: string | number | undefined) =>
              name === "Revenue (30d)" ? [money(Number(value)), name] : [`${Number(value)} units`, name ?? ""]
            }
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Bar yAxisId="units" dataKey="units" name="Units sold (30d)" fill="#3E6FBF" radius={[3, 3, 0, 0]} />
          <Bar yAxisId="revenue" dataKey="revenue" name="Revenue (30d)" fill="#D4973A" radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

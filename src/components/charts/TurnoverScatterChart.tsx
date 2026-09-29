"use client";

import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  type TooltipValueType,
} from "recharts";
import type { ClassifiedSku, FsnClass } from "@/lib/analytics/types";

const FSN_COLORS: Record<FsnClass, string> = {
  "Fast-moving": "#2E7D32",
  "Slow-moving": "#E0932A",
  "Non-moving": "#C0392B",
};

function money(n: number): string {
  return `$${n.toLocaleString("en-US", { maximumFractionDigits: 0 })}`;
}

/** Report Figure 6 — turnover ratio vs. revenue; bubble size = inventory value. */
export function TurnoverScatterChart({ data }: { data: ClassifiedSku[] }) {
  const series: FsnClass[] = ["Fast-moving", "Slow-moving", "Non-moving"];

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4 shadow-sm">
      <div className="text-sm font-medium text-slate-600 mb-2">
        Annualised turnover vs. 30-day revenue — bubble size = inventory value at cost
      </div>
      <ResponsiveContainer width="100%" height={380}>
        <ScatterChart margin={{ top: 10, right: 20, left: 0, bottom: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis
            type="number"
            dataKey="itr_annualised"
            name="Turnover ratio"
            tick={{ fontSize: 11 }}
            label={{ value: "Annualised turnover ratio (ITR)", position: "insideBottom", offset: -5, fontSize: 11 }}
          />
          <YAxis
            type="number"
            dataKey="revenue_30d"
            name="Revenue"
            tick={{ fontSize: 11 }}
            tickFormatter={money}
            label={{ value: "30-day revenue", angle: -90, position: "insideLeft", fontSize: 11 }}
          />
          <ZAxis type="number" dataKey="inventory_value" range={[40, 500]} name="Inventory value" />
          <Tooltip
            cursor={{ strokeDasharray: "3 3" }}
            formatter={(value: TooltipValueType | undefined, name: string | number | undefined) => {
              const n = Number(value);
              if (name === "Revenue") return [money(n), name];
              if (name === "Inventory value") return [money(n), name];
              return [n.toFixed(1) + "×", name ?? ""];
            }}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          {series.map((cls) => (
            <Scatter
              key={cls}
              name={cls}
              data={data.filter((d) => d.fsn_class === cls)}
              fill={FSN_COLORS[cls]}
              fillOpacity={0.75}
            />
          ))}
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}

"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  type TooltipValueType,
} from "recharts";
import type { FsnBreakdownRow } from "@/lib/analytics/summary";

const FSN_COLORS: Record<string, string> = {
  "Fast-moving": "#2E7D32",
  "Slow-moving": "#E0932A",
  "Non-moving": "#C0392B",
};

function money(n: number): string {
  return `$${n.toLocaleString("en-US", { maximumFractionDigits: 0 })}`;
}

/** Report Figure 1 — SKU count and inventory value tied up, by movement class. */
export function FsnDistributionChart({ data }: { data: FsnBreakdownRow[] }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div className="bg-white rounded-lg border border-slate-200 p-4 shadow-sm">
        <div className="text-sm font-medium text-slate-600 mb-2">SKU count by movement class</div>
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
            <XAxis dataKey="fsn_class" tick={{ fontSize: 11 }} interval={0} />
            <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
            <Tooltip formatter={(v: TooltipValueType | undefined) => [`${Number(v)} SKUs`, "Count"]} />
            <Bar dataKey="skuCount" radius={[4, 4, 0, 0]}>
              {data.map((d) => (
                <Cell key={d.fsn_class} fill={FSN_COLORS[d.fsn_class]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="bg-white rounded-lg border border-slate-200 p-4 shadow-sm">
        <div className="text-sm font-medium text-slate-600 mb-2">Inventory value tied up by class</div>
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
            <XAxis dataKey="fsn_class" tick={{ fontSize: 11 }} interval={0} />
            <YAxis tick={{ fontSize: 11 }} tickFormatter={money} />
            <Tooltip formatter={(v: TooltipValueType | undefined) => [money(Number(v)), "Inventory value"]} />
            <Bar dataKey="inventoryValue" radius={[4, 4, 0, 0]}>
              {data.map((d) => (
                <Cell key={d.fsn_class} fill={FSN_COLORS[d.fsn_class]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

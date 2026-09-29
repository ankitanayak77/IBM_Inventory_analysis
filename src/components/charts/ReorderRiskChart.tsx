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
  type TooltipPayloadEntry,
} from "recharts";
import type { ClassifiedSku } from "@/lib/analytics/types";

const STATUS_COLORS: Record<string, string> = {
  "Reorder Now": "#C0392B",
  "Low - Monitor": "#E0932A",
};

/** Report Figure 4 — days of stock remaining, for every SKU at or near reorder point. */
export function ReorderRiskChart({ data }: { data: ClassifiedSku[] }) {
  const chartData = data.map((r) => ({
    label: `${r.product_name} (${r.size})`,
    days: Math.round(r.days_of_stock),
    status: r.stock_status,
    onHand: r.quantity_on_hand,
    rop: r.reorder_point,
  }));

  if (chartData.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-slate-200 p-6 shadow-sm text-sm text-slate-500">
        No SKUs are currently at or near their reorder point.
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4 shadow-sm">
      <div className="text-sm font-medium text-slate-600 mb-2">Days of stock remaining at current sales rate</div>
      <ResponsiveContainer width="100%" height={Math.max(180, chartData.length * 46)}>
        <BarChart
          data={chartData}
          layout="vertical"
          margin={{ top: 5, right: 60, left: 10, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e2e8f0" />
          <XAxis type="number" tick={{ fontSize: 11 }} label={{ value: "Days left", position: "insideBottom", offset: -5, fontSize: 11 }} />
          <YAxis type="category" dataKey="label" tick={{ fontSize: 11 }} width={170} />
          <Tooltip
            formatter={(value: TooltipValueType | undefined, _name: string | number | undefined, item: TooltipPayloadEntry) => {
              const p = item?.payload as { onHand: number; rop: number } | undefined;
              return [`${Number(value)}d (on hand ${p?.onHand} / ROP ${p?.rop})`, "Days left"];
            }}
          />
          <Bar dataKey="days" radius={[0, 4, 4, 0]} barSize={22}>
            {chartData.map((d, i) => (
              <Cell key={i} fill={STATUS_COLORS[d.status] ?? "#8A93A6"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <div className="flex gap-4 mt-2 text-xs text-slate-500">
        <span className="flex items-center gap-1">
          <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ backgroundColor: "#C0392B" }} /> Reorder Now
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ backgroundColor: "#E0932A" }} /> Low - Monitor
        </span>
      </div>
    </div>
  );
}

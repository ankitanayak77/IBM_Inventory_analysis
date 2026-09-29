"use client";

import type { FsnAbcMatrixCell } from "@/lib/analytics/summary";
import type { FsnClass, AbcClass } from "@/lib/analytics/types";

const FSN_ORDER: FsnClass[] = ["Fast-moving", "Slow-moving", "Non-moving"];
const ABC_ORDER: AbcClass[] = ["A", "B", "C"];
const ABC_LABELS: Record<AbcClass, string> = { A: "A (high value)", B: "B (medium)", C: "C (low value)" };

/**
 * Report Figure 3 — FSN x ABC priority matrix.
 * Deliberately built as a plain colour-scaled grid rather than forced into
 * a Recharts chart type: Recharts has no native heatmap primitive, and a
 * scatter/treemap hack here would be less honest than a styled table.
 */
export function FsnAbcMatrix({ cells }: { cells: FsnAbcMatrixCell[] }) {
  const maxCount = Math.max(...cells.map((c) => c.count), 1);
  const countOf = (fsn: FsnClass, abc: AbcClass) =>
    cells.find((c) => c.fsn_class === fsn && c.abc_class === abc)?.count ?? 0;

  function cellStyle(count: number) {
    const intensity = count / maxCount; // 0..1
    // Interpolate from pale to the report's red accent, matching Figure 3's palette.
    const bg = `rgba(192, 57, 43, ${0.12 + intensity * 0.75})`;
    const textDark = intensity < 0.45;
    return { backgroundColor: bg, color: textDark ? "#0F1F3D" : "#FFFFFF" };
  }

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4 shadow-sm">
      <div className="text-sm font-medium text-slate-600 mb-3">SKU counts crossing movement speed against value class</div>
      <div className="overflow-x-auto">
        <table className="border-collapse w-full max-w-xl">
          <thead>
            <tr>
              <th className="p-2" />
              {ABC_ORDER.map((abc) => (
                <th key={abc} className="p-2 text-xs font-medium text-slate-500 text-center">
                  {ABC_LABELS[abc]}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {FSN_ORDER.map((fsn) => (
              <tr key={fsn}>
                <td className="p-2 text-xs font-medium text-slate-500 whitespace-nowrap">{fsn}</td>
                {ABC_ORDER.map((abc) => {
                  const count = countOf(fsn, abc);
                  return (
                    <td key={abc} className="p-1">
                      <div
                        className="rounded-md flex items-center justify-center h-16 text-lg font-bold transition-colors"
                        style={cellStyle(count)}
                      >
                        {count}
                      </div>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

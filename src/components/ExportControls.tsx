"use client";

import { useState } from "react";
import type { AnalysisResult } from "@/lib/analytics/analyze";
import { rowsToCsv, recommendationsToCsv, downloadTextFile } from "@/lib/export/toCsv";

interface ExportControlsProps {
  result: AnalysisResult;
  sourceLabel: string;
}

/** Report FR-8: "Export a filtered SKU list ... as CSV or PDF." */
export function ExportControls({ result, sourceLabel }: ExportControlsProps) {
  const [pdfStatus, setPdfStatus] = useState<"idle" | "loading" | "error">("idle");
  const [pdfError, setPdfError] = useState<string | null>(null);

  function handleDownloadFullCsv() {
    const csv = rowsToCsv(result.rows);
    downloadTextFile(csv, "inventory-full-list.csv", "text/csv;charset=utf-8;");
  }

  function handleDownloadReorderCsv() {
    const csv = rowsToCsv(result.reorderRisk);
    downloadTextFile(csv, "inventory-reorder-risk.csv", "text/csv;charset=utf-8;");
  }

  function handleDownloadRecommendationsCsv() {
    const items = result.recommendations?.items ?? [];
    const csv = recommendationsToCsv(items);
    downloadTextFile(csv, "inventory-recommendations-purchase-orders.csv", "text/csv;charset=utf-8;");
  }

  async function handleDownloadPdf() {
    setPdfStatus("loading");
    setPdfError(null);
    try {
      const response = await fetch("/api/export/pdf", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ result, sourceLabel }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.error ?? `PDF export failed (HTTP ${response.status}).`);
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "inventory-analysis-report.pdf";
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      URL.revokeObjectURL(url);
      setPdfStatus("idle");
    } catch (err) {
      setPdfStatus("error");
      setPdfError(err instanceof Error ? err.message : "PDF export failed.");
    }
  }

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4 shadow-sm">
      <div className="text-sm font-medium text-slate-600 mb-3">Export</div>
      <div className="flex flex-wrap gap-2">
        <button
          onClick={handleDownloadFullCsv}
          className="text-sm font-medium px-3 py-1.5 rounded-md border border-slate-300 text-slate-700 hover:bg-slate-50"
        >
          Full list (CSV)
        </button>
        <button
          onClick={handleDownloadReorderCsv}
          disabled={result.reorderRisk.length === 0}
          className="text-sm font-medium px-3 py-1.5 rounded-md border border-slate-300 text-slate-700 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Reorder-risk list only (CSV) — {result.reorderRisk.length}
        </button>
        <button
          onClick={handleDownloadRecommendationsCsv}
          disabled={!result.recommendations || result.recommendations.items.length === 0}
          className="text-sm font-medium px-3 py-1.5 rounded-md border border-amber-300 bg-amber-50 text-amber-900 hover:bg-amber-100 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Purchase Orders & Recommendations (CSV) — {result.recommendations?.items.length ?? 0}
        </button>
        <button
          onClick={handleDownloadPdf}
          disabled={pdfStatus === "loading"}
          className="text-sm font-medium px-3 py-1.5 rounded-md bg-[var(--color-navy)] text-white hover:opacity-90 disabled:opacity-50"
        >
          {pdfStatus === "loading" ? "Generating PDF…" : "Full report & recommendations (PDF)"}
        </button>
      </div>
      {pdfError && <p className="text-sm text-red-600 mt-2">{pdfError}</p>}
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import type { AnalysisResult } from "@/lib/analytics/analyze";

interface DatasetSummary {
  id: number;
  sourceLabel: string;
  uploadedAt: string;
  skuCount: number;
  rejectedRowCount: number;
}

interface HistoryPanelProps {
  onLoad: (result: AnalysisResult, sourceLabel: string) => void;
}

/**
 * Report Chapter 15 / Phase 2 — the frontend half of "persisted history":
 * lists past analysis runs via GET /api/datasets and loads one back via
 * GET /api/datasets/[id]. Renders nothing but a quiet, honest note when
 * no database is configured (Phase 2 is optional — see /api/upload's and
 * /api/datasets's own comments on why), rather than showing a broken or
 * misleading empty history list.
 */
export function HistoryPanel({ onLoad }: HistoryPanelProps) {
  const [datasets, setDatasets] = useState<DatasetSummary[]>([]);
  const [databaseConfigured, setDatabaseConfigured] = useState<boolean | null>(null);
  const [loadingId, setLoadingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/datasets")
      .then((r) => r.json())
      .then((body) => {
        setDatabaseConfigured(body.databaseConfigured);
        setDatasets(body.datasets ?? []);
      })
      .catch(() => setDatabaseConfigured(false));
  }, []);

  async function handleLoad(id: number, sourceLabel: string) {
    setLoadingId(id);
    setError(null);
    try {
      const response = await fetch(`/api/datasets/${id}`);
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.error ?? `Failed to load dataset ${id}.`);
      }
      const result = await response.json();
      onLoad(result, sourceLabel);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load that dataset.");
    } finally {
      setLoadingId(null);
    }
  }

  if (databaseConfigured === null) return null; // still loading; avoid a flash of empty state
  if (!databaseConfigured) {
    return (
      <div className="bg-white rounded-lg border border-slate-200 p-4 shadow-sm text-sm text-slate-500">
        Upload history isn&apos;t available — no database is configured for this deployment. Every upload still
        works normally; it just isn&apos;t saved between sessions. See <code>BUILD_NOTES.md</code> (&quot;Phase
        2&quot;) for how to enable it.
      </div>
    );
  }
  if (datasets.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-slate-200 p-4 shadow-sm text-sm text-slate-500">
        No past uploads yet — analyze a CSV above and it&apos;ll show up here.
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4 shadow-sm">
      <div className="text-sm font-medium text-slate-600 mb-3">Upload History</div>
      <ul className="divide-y divide-slate-100">
        {datasets.map((d) => (
          <li key={d.id} className="flex items-center justify-between py-2 text-sm">
            <div>
              <span className="font-medium text-[var(--color-navy)]">{d.sourceLabel}</span>
              <span className="text-slate-400 ml-2">
                {new Date(d.uploadedAt).toLocaleString()} · {d.skuCount} SKUs
                {d.rejectedRowCount > 0 && `, ${d.rejectedRowCount} rejected`}
              </span>
            </div>
            <button
              onClick={() => handleLoad(d.id, d.sourceLabel)}
              disabled={loadingId === d.id}
              className="text-xs font-medium px-2.5 py-1 rounded-md border border-slate-300 text-slate-700 hover:bg-slate-50 disabled:opacity-50"
            >
              {loadingId === d.id ? "Loading…" : "View"}
            </button>
          </li>
        ))}
      </ul>
      {error && <p className="text-sm text-red-600 mt-2">{error}</p>}
    </div>
  );
}

"use client";

import { useState, useRef, type FormEvent } from "react";
import type { AnalysisResult } from "@/lib/analytics/analyze";
import type { ClassifiedSku } from "@/lib/analytics/types";

interface EmailAlertStatus {
  sent: boolean;
  skipReason?: string;
  error?: string;
}

interface UploadFormProps {
  onResult: (result: AnalysisResult, fileName: string, newlyAtRisk: ClassifiedSku[] | null, emailAlert: EmailAlertStatus | null) => void;
  onReset: () => void;
  isShowingUpload: boolean;
}

/**
 * Report FR-1 made real: lets a shop owner load their own CSV (matching the
 * Section 3.1 schema) instead of only ever viewing the bundled sample data.
 * Posts to /api/upload — a Route Handler, not a Server Action, to sidestep
 * the documented Server Action body-size-limit issue (see route.ts).
 */
export function UploadForm({ onResult, onReset, isShowingUpload }: UploadFormProps) {
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [rejectedCount, setRejectedCount] = useState<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const file = fileInputRef.current?.files?.[0];
    if (!file) {
      setStatus("error");
      setErrorMessage("Choose a CSV file first.");
      return;
    }
    if (!file.name.toLowerCase().endsWith(".csv")) {
      setStatus("error");
      setErrorMessage("That doesn't look like a .csv file.");
      return;
    }

    setStatus("loading");
    setErrorMessage(null);
    setRejectedCount(null);

    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await fetch("/api/upload", { method: "POST", body: formData });
      const body = await response.json();

      if (!response.ok) {
        setStatus("error");
        setErrorMessage(body.error ?? `Upload failed (HTTP ${response.status}).`);
        return;
      }

      setStatus("idle");
      setRejectedCount(body.rejectedRowCount ?? 0);
      onResult(body as AnalysisResult, file.name, body.newlyAtRisk ?? null, body.emailAlert ?? null);
    } catch {
      setStatus("error");
      setErrorMessage("Could not reach the server. Check your connection and try again.");
    }
  }

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4 shadow-sm">
      <form onSubmit={handleSubmit} className="flex flex-wrap items-center gap-3">
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,text/csv"
          className="text-sm text-slate-600 file:mr-3 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:bg-[var(--color-navy)] file:text-white file:text-sm file:font-medium hover:file:opacity-90 file:cursor-pointer cursor-pointer"
        />
        <button
          type="submit"
          disabled={status === "loading"}
          className="bg-[var(--color-gold)] text-white text-sm font-medium px-4 py-1.5 rounded-md disabled:opacity-50"
        >
          {status === "loading" ? "Analyzing…" : "Analyze CSV"}
        </button>
        {isShowingUpload && (
          <button
            type="button"
            onClick={() => {
              onReset();
              setErrorMessage(null);
              setRejectedCount(null);
              if (fileInputRef.current) fileInputRef.current.value = "";
            }}
            className="text-sm text-slate-500 underline underline-offset-2"
          >
            Back to sample data
          </button>
        )}
      </form>

      {errorMessage && <p className="text-sm text-red-600 mt-2">{errorMessage}</p>}
      {rejectedCount !== null && rejectedCount > 0 && (
        <p className="text-sm text-amber-600 mt-2">
          {rejectedCount} row(s) were rejected during import (missing fields, bad numbers, or duplicate SKUs) — see
          server logs for details. The remaining rows were analyzed normally.
        </p>
      )}
      <p className="text-xs text-slate-400 mt-2">
        Expected columns: sku, product_name, category, size, color, quantity_on_hand, reorder_point, cost_per_unit,
        retail_price, last_restock_date, units_sold_30d, supplier, season.
      </p>
    </div>
  );
}

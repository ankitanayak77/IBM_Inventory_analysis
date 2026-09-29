import Papa from "papaparse";
import type { RawSkuRow } from "./types";

/** One rejected row, with a human-readable reason — FR-1 / Section 6.2 (Reliability):
 *  a malformed row is rejected with a clear reason, not silently dropped. */
export interface RejectedRow {
  rowNumber: number; // 1-based, matches the CSV line (excluding header)
  raw: Record<string, string>;
  reason: string;
}

export interface ParseResult {
  rows: RawSkuRow[];
  rejected: RejectedRow[];
}

const REQUIRED_COLUMNS = [
  "sku",
  "product_name",
  "category",
  "size",
  "color",
  "quantity_on_hand",
  "reorder_point",
  "cost_per_unit",
  "retail_price",
  "last_restock_date",
  "units_sold_30d",
  "supplier",
  "season",
] as const;

const NUMERIC_COLUMNS = [
  "quantity_on_hand",
  "reorder_point",
  "cost_per_unit",
  "retail_price",
  "units_sold_30d",
] as const;

function isBlank(v: string | undefined): boolean {
  return v === undefined || v.trim() === "";
}

/**
 * Parses and validates a raw inventory/sales CSV against the schema in
 * Report Section 3.1. Every row is either a clean RawSkuRow or a RejectedRow
 * with a stated reason — nothing is silently coerced or dropped.
 */
export function parseInventoryCsv(csvText: string): ParseResult {
  const parsed = Papa.parse<Record<string, string>>(csvText, {
    header: true,
    skipEmptyLines: true,
  });

  const headerFields = parsed.meta.fields ?? [];
  const missingColumns = REQUIRED_COLUMNS.filter((c) => !headerFields.includes(c));
  if (missingColumns.length > 0) {
    throw new Error(
      `CSV is missing required column(s): ${missingColumns.join(", ")}. Expected columns: ${REQUIRED_COLUMNS.join(", ")}.`
    );
  }

  const rows: RawSkuRow[] = [];
  const rejected: RejectedRow[] = [];

  parsed.data.forEach((raw, idx) => {
    const rowNumber = idx + 1;

    // 1) Required-field presence check.
    const emptyField = REQUIRED_COLUMNS.find((c) => isBlank(raw[c]));
    if (emptyField) {
      rejected.push({ rowNumber, raw, reason: `Missing value in required column "${emptyField}".` });
      return;
    }

    // 2) Duplicate SKU check (within this file).
    if (rows.some((r) => r.sku === raw.sku)) {
      rejected.push({ rowNumber, raw, reason: `Duplicate SKU "${raw.sku}" — first occurrence kept.` });
      return;
    }

    // 3) Numeric-field validity check.
    const badNumeric = NUMERIC_COLUMNS.find((c) => {
      const n = Number(raw[c]);
      return !Number.isFinite(n) || n < 0;
    });
    if (badNumeric) {
      rejected.push({
        rowNumber,
        raw,
        reason: `Column "${badNumeric}" must be a non-negative number, got "${raw[badNumeric]}".`,
      });
      return;
    }

    rows.push({
      sku: raw.sku,
      product_name: raw.product_name,
      category: raw.category,
      size: raw.size,
      color: raw.color,
      quantity_on_hand: Number(raw.quantity_on_hand),
      reorder_point: Number(raw.reorder_point),
      cost_per_unit: Number(raw.cost_per_unit),
      retail_price: Number(raw.retail_price),
      last_restock_date: raw.last_restock_date,
      units_sold_30d: Number(raw.units_sold_30d),
      supplier: raw.supplier,
      season: raw.season,
    });
  });

  return { rows, rejected };
}

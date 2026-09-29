import Papa from "papaparse";
import type { ClassifiedSku } from "@/lib/analytics/types";
import type { RecommendationItem } from "@/lib/analytics/recommendations";

/**
 * Report FR-8: "Export a filtered SKU list (e.g. 'Reorder Now' only) as
 * CSV or PDF." CSV export runs fully client-side — the data is already in
 * the browser (DashboardShell's state), so there is no reason to round-trip
 * it through the server just to convert it to text. Uses papaparse's
 * `unparse` (already a dependency, and verified to correctly quote/escape
 * embedded commas — see conversation) rather than hand-joining strings.
 */

const EXPORT_COLUMNS: { key: keyof ClassifiedSku; label: string }[] = [
  { key: "sku", label: "SKU" },
  { key: "product_name", label: "Product" },
  { key: "size", label: "Size" },
  { key: "color", label: "Color" },
  { key: "category", label: "Category" },
  { key: "supplier", label: "Supplier" },
  { key: "quantity_on_hand", label: "Qty On Hand" },
  { key: "reorder_point", label: "Reorder Point" },
  { key: "units_sold_30d", label: "Units Sold (30d)" },
  { key: "itr_annualised", label: "Turnover Ratio (annualised)" },
  { key: "days_of_stock", label: "Days Of Stock Left" },
  { key: "fsn_class", label: "FSN Class" },
  { key: "abc_class", label: "ABC Class" },
  { key: "stock_status", label: "Stock Status" },
  { key: "priority_tag", label: "Priority" },
  { key: "inventory_value", label: "Inventory Value ($)" },
  { key: "revenue_30d", label: "Revenue 30d ($)" },
];

function round2(n: number): number | string {
  if (!Number.isFinite(n)) return n === Infinity ? "∞" : n; // NaN never reaches here post-fix, but stay defensive
  return Math.round(n * 100) / 100;
}

export function rowsToCsv(rows: ClassifiedSku[]): string {
  const fields = EXPORT_COLUMNS.map((c) => c.label);
  const data = rows.map((row) =>
    EXPORT_COLUMNS.map(({ key }) => {
      const value = row[key];
      return typeof value === "number" ? round2(value) : String(value);
    })
  );
  // Using the {fields, data} form deliberately, not unparse(records, {columns}):
  // verified that the latter silently drops the header row entirely when
  // `records` is empty (papaparse ignores the `columns` option in that case),
  // which would produce a blank file for a filtered list with zero matches
  // (e.g. exporting "Reorder Now" SKUs when there happen to be none).
  return Papa.unparse({ fields, data });
}

/** Triggers a browser download of `content` as a file named `filename`. */
export function downloadTextFile(content: string, filename: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}

/**
 * Exports actionable replenishment orders, liquidation candidates, and recommendations as CSV.
 * Directly usable as a purchase order requisition or clearance action sheet.
 */
export function recommendationsToCsv(items: RecommendationItem[]): string {
  const fields = [
    "SKU",
    "Product",
    "Category",
    "Supplier",
    "Action Type",
    "Urgency",
    "Current Stock",
    "Reorder Point",
    "Days Left",
    "Suggested Order Qty",
    "Unit Cost ($)",
    "Estimated Cost ($)",
    "Recommended Action",
    "FSN Class",
    "ABC Class",
    "Stock Status",
    "Priority Tag",
  ];
  const data = items.map((item) => [
    item.sku,
    item.product_name,
    item.category,
    item.supplier,
    item.type,
    item.urgency,
    item.actionData.currentStock,
    item.actionData.reorderPoint,
    Number.isFinite(item.actionData.daysOfStock) ? Math.round(item.actionData.daysOfStock) : "∞",
    item.actionData.suggestedOrderQty,
    round2(item.actionData.unitCost),
    round2(item.actionData.estimatedCost),
    item.actionData.recommendedAction,
    item.actionData.fsnClass,
    item.actionData.abcClass,
    item.actionData.stockStatus,
    item.actionData.priorityTag,
  ]);
  return Papa.unparse({ fields, data });
}

export interface SupplierPoOptions {
  poNumber?: string;
  orderDate?: string;
}

/**
 * Generates a vendor-ready Purchase Order (PO) requisition in CSV format for a specific supplier.
 * Aligns with NetSuite / ERP procurement templates for direct vendor dispatch.
 */
export function supplierPoToCsv(
  supplier: string,
  items: RecommendationItem[],
  options?: SupplierPoOptions
): string {
  const supplierItems = items.filter(
    (i) => i.type === "replenishment" && i.supplier === supplier && i.actionData.suggestedOrderQty > 0
  );

  const cleanSupp = supplier.replace(/[^a-zA-Z0-9]/g, "").slice(0, 6).toUpperCase();
  const poNumber = options?.poNumber ?? `PO-${cleanSupp || "SUPP"}-${new Date().toISOString().slice(0, 10).replace(/-/g, "")}`;
  const orderDate = options?.orderDate ?? new Date().toISOString().slice(0, 10);

  const fields = [
    "PO Number",
    "Order Date",
    "Supplier",
    "SKU",
    "Product Description",
    "Category",
    "Current Stock",
    "Reorder Point",
    "Order Quantity",
    "Unit Cost ($)",
    "Line Total ($)",
    "Stock Status",
    "Priority",
  ];

  const data = supplierItems.map((item) => [
    poNumber,
    orderDate,
    supplier,
    item.sku,
    item.product_name,
    item.category,
    item.actionData.currentStock,
    item.actionData.reorderPoint,
    item.actionData.suggestedOrderQty,
    round2(item.actionData.unitCost),
    round2(item.actionData.estimatedCost),
    item.actionData.stockStatus,
    item.actionData.priorityTag,
  ]);

  return Papa.unparse({ fields, data });
}


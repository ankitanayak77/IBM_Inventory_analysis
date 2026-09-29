// Core types for the Inventory Analysis engine.
// Field names and semantics match Section 3.1 / 3.3 of the project report exactly,
// so results here are directly comparable to the Python-verified output.

export interface RawSkuRow {
  sku: string;
  product_name: string;
  category: string;
  size: string;
  color: string;
  quantity_on_hand: number;
  reorder_point: number;
  cost_per_unit: number;
  retail_price: number;
  last_restock_date: string;
  units_sold_30d: number;
  supplier: string;
  season: string;
}

export type FsnClass = "Fast-moving" | "Slow-moving" | "Non-moving";
export type AbcClass = "A" | "B" | "C";
export type StockStatus = "Reorder Now" | "Low - Monitor" | "Healthy";
export type PriorityTag =
  | "Critical - protect availability"
  | "High-value at risk - investigate"
  | "Discontinue candidate"
  | "Undervalued fast mover"
  | "Routine review";

export interface ClassifiedSku extends RawSkuRow {
  inventory_value: number;
  revenue_30d: number;
  gross_margin_30d: number;
  itr_annualised: number;
  days_of_stock: number;
  fsn_class: FsnClass;
  abc_class: AbcClass;
  abc_revenue_share: number;
  abc_cumulative_share: number;
  stock_status: StockStatus;
  priority_tag: PriorityTag;
}

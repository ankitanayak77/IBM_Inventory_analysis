/**
 * Deterministic synthetic inventory-CSV generator, used by both the
 * standalone `scripts/generate-load-test-data.ts` (for a human to inspect
 * an on-disk copy) and the permanent Vitest performance/edge-case suite
 * (`src/lib/analytics/__tests__/scale.test.ts`), so both always exercise
 * exactly the same data.
 *
 * Value ranges (categories, seasons, suppliers, price $24-148, cost
 * $8.5-58, cost/price ratio 0.30-0.39) are taken directly from the real
 * 50-SKU sample dataset's actual min/max — not invented. A seeded PRNG
 * (mulberry32, not Math.random) makes every generated row reproducible
 * across runs and machines.
 */

function mulberry32(seed: number) {
  return function () {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const CATEGORIES = ["Accessories", "Bottoms", "Dresses", "Footwear", "Outerwear", "Tops"] as const;
const SEASONS = ["Fall/Winter", "Spring/Summer", "Year-Round"] as const;
const SUPPLIERS = [
  "Accessory World", "Bella Basics", "Cozy Knits Inc", "Denim Dreams", "Footwear First",
  "Jewelry Junction", "Luxe Leather Co", "Professional Plus", "Summer Styles Co",
] as const;
const SIZES = ["XS", "S", "M", "L", "XL"] as const;
const COLORS = ["Black", "White", "Navy", "Cream", "Red", "Blue", "Green", "Grey"] as const;

const CSV_HEADER = [
  "sku", "product_name", "category", "size", "color", "quantity_on_hand", "reorder_point",
  "cost_per_unit", "retail_price", "last_restock_date", "units_sold_30d", "supplier", "season",
];

export interface GenerateOptions {
  count: number;
  seed?: number;
  /** Fraction of rows deliberately given quantity_on_hand = 0 (the edge
   *  case discovered via load-testing that the classification engine must
   *  handle without producing NaN — see classify.ts's withDerivedMetrics).
   *  Default 0.0165 reproduces the ~165-in-10,000 rate first observed. */
  zeroQuantityFraction?: number;
}

/** Generates the CSV text (header + N rows) matching Report Section 3.1's schema. */
export function generateSyntheticInventoryCsv({
  count,
  seed = 20260923,
  zeroQuantityFraction = 0.0165,
}: GenerateOptions): string {
  const rand = mulberry32(seed);
  const pick = <T,>(arr: readonly T[]): T => arr[Math.floor(rand() * arr.length)];
  const randInt = (min: number, max: number) => Math.floor(min + rand() * (max - min + 1));
  const randFloat = (min: number, max: number, decimals = 2) => {
    const v = min + rand() * (max - min);
    return Math.round(v * 10 ** decimals) / 10 ** decimals;
  };

  const lines: string[] = [CSV_HEADER.join(",")];

  for (let i = 1; i <= count; i++) {
    const sku = `SYN${String(i).padStart(6, "0")}`;
    const category = pick(CATEGORIES);
    const productName = `${category} Item ${Math.ceil(i / SIZES.length)}`;
    const size = pick(SIZES);
    const color = pick(COLORS);

    const retailPrice = randFloat(24, 148, 2);
    const costRatio = randFloat(0.3, 0.39, 4);
    const costPerUnit = Math.round(retailPrice * costRatio * 100) / 100;

    const quantityOnHand = rand() < zeroQuantityFraction ? 0 : randInt(1, 60);
    const reorderPoint = randInt(5, 20);
    const unitsSold30d = randInt(0, 40);

    const month = randInt(1, 12);
    const day = randInt(1, 28);
    const lastRestockDate = `2024-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;

    lines.push(
      [
        sku, productName, category, size, color, quantityOnHand, reorderPoint,
        costPerUnit, retailPrice, lastRestockDate, unitsSold30d, pick(SUPPLIERS), pick(SEASONS),
      ].join(",")
    );
  }

  return lines.join("\n") + "\n";
}

/**
 * CLI wrapper: writes an on-disk copy of the synthetic 10,000-SKU dataset
 * for manual inspection. The actual generation logic lives in
 * src/test-fixtures/generateSyntheticInventory.ts, which the permanent
 * Vitest performance suite (scale.test.ts) imports directly — this script
 * and that test always use the exact same generator, never a duplicate.
 */
import { writeFileSync } from "fs";
import path from "path";
import { generateSyntheticInventoryCsv } from "../src/test-fixtures/generateSyntheticInventory";

const csv = generateSyntheticInventoryCsv({ count: 10000 });
const outPath = path.join(process.cwd(), "src/data/synthetic_10000sku.csv");
writeFileSync(outPath, csv, "utf-8");
console.log(`Wrote 10000 rows to ${outPath}`);

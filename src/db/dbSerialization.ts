/**
 * Converts a Drizzle `numeric` (string-mode) column value back into a
 * real JS number — including "Infinity", which `Number()` correctly
 * parses to the actual Infinity value. See src/db/schema.ts's comment
 * for why itr_annualised and days_of_stock are stored this way instead
 * of `numeric(..., { mode: "number" })` or `doublePrecision` (both
 * confirmed, by direct testing against a real Postgres instance, to
 * silently return `null` for Infinity through Drizzle's own read path).
 */
export function parseNumericString(value: string): number {
  const n = Number(value);
  if (Number.isNaN(n) && value !== "NaN") {
    throw new Error(`Could not parse "${value}" as a number.`);
  }
  return n;
}

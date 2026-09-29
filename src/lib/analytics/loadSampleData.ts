import { readFileSync } from "fs";
import path from "path";
import { analyzeCsvText, type AnalysisResult } from "./analyze";

/**
 * Server-only helper: loads the bundled sample dataset (Report Section 3.1)
 * and runs it through the same `analyzeCsvText` pipeline the CSV-upload API
 * route uses, so the initial server-rendered dashboard and an uploaded
 * dataset are guaranteed to be computed identically.
 */
export function loadAndClassifySampleData(): AnalysisResult {
  const csvPath = path.join(process.cwd(), "src/data/retail_inventory.csv");
  const csvText = readFileSync(csvPath, "utf-8");
  return analyzeCsvText(csvText);
}

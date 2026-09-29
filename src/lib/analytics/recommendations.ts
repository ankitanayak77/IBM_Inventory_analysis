import type { ClassifiedSku, FsnClass, AbcClass, StockStatus, PriorityTag } from "./types";
import type { PortfolioKpis } from "./summary";

export type RecommendationUrgency = "Immediate" | "High" | "Medium" | "Strategic";

export type RecommendationType =
  | "replenishment"
  | "liquidation"
  | "pricing_margin"
  | "safety_stock"
  | "supplier_risk";

export interface RecommendationItem {
  id: string;
  sku: string;
  product_name: string;
  category: string;
  supplier: string;
  type: RecommendationType;
  urgency: RecommendationUrgency;
  title: string;
  description: string;
  financialImpact: {
    type: "capital_required" | "capital_recovery" | "margin_upside" | "risk_mitigation";
    amount: number;
  };
  actionData: {
    currentStock: number;
    reorderPoint: number;
    unitsSold30d: number;
    daysOfStock: number;
    suggestedOrderQty: number;
    unitCost: number;
    retailPrice: number;
    estimatedCost: number;
    recommendedAction: string;
    fsnClass: FsnClass;
    abcClass: AbcClass;
    stockStatus: StockStatus;
    priorityTag: PriorityTag;
  };
}

export interface SupplierRiskSummary {
  supplier: string;
  totalSkus: number;
  atRiskSkus: number;
  criticalAtRiskSkus: number; // A-Fast SKUs at risk
  totalInventoryValue: number;
  estimatedReplenishmentCost: number;
}

export interface InventoryRecommendationsSummary {
  healthScore: number; // 0 to 100
  healthGrade: "Excellent" | "Good" | "Needs Attention" | "Critical Risk";
  totalReplenishmentCost: number;
  trappedCapitalInDeadStock: number;
  trappedCapitalInSlowMoving: number;
  potentialCapitalRecovery: number;
  netWorkingCapitalImpact: number; // Recovery - Replenishment
  immediateActionCount: number;
  items: RecommendationItem[];
  supplierRiskSummary: SupplierRiskSummary[];
  executiveSummaryText: string;
}

/**
 * Calculates Suggested Order Quantity (SOQ) based on standard APICS replenishment logic:
 * Target Stock Level = Reorder Point + Cycle Stock Buffer (30 days of average demand)
 * Suggested Order Quantity = max(0, Target Stock Level - Current Stock)
 */
export function calculateSuggestedOrderQty(
  quantityOnHand: number,
  reorderPoint: number,
  unitsSold30d: number,
  targetDaysBuffer: number = 30
): number {
  const dailyDemand = unitsSold30d / 30;
  const cycleStockBuffer = Math.ceil(dailyDemand * targetDaysBuffer);
  const targetStockLevel = Math.max(reorderPoint * 2, reorderPoint + cycleStockBuffer);

  if (quantityOnHand >= targetStockLevel) {
    return 0;
  }
  return Math.max(1, targetStockLevel - quantityOnHand);
}

/**
 * Computes a weighted 0-100 inventory health score based on 4 industry pillars:
 * 1. Availability & Stockout Risk (35% weight)
 * 2. Capital Efficiency & Dead Stock Ratio (30% weight)
 * 3. Inventory Velocity & Turnover Rate (20% weight)
 * 4. Gross Margin Health (15% weight)
 */
export function computeInventoryHealthScore(
  totalSkus: number,
  atRiskCount: number,
  reorderNowCount: number,
  totalInventoryValue: number,
  deadStockValue: number,
  medianItr: number,
  grossMarginPct: number
): { score: number; grade: "Excellent" | "Good" | "Needs Attention" | "Critical Risk" } {
  if (totalSkus === 0) {
    return { score: 100, grade: "Excellent" };
  }

  // Pillar 1: Availability (max 35 pts)
  // Severe deduction for "Reorder Now", moderate deduction for "Low - Monitor"
  const reorderNowRatio = reorderNowCount / totalSkus;
  const atRiskRatio = (atRiskCount - reorderNowCount) / totalSkus;
  const availabilityScore = Math.max(0, 35 - reorderNowRatio * 100 - atRiskRatio * 40);

  // Pillar 2: Capital Efficiency (max 30 pts)
  // Percent of inventory value locked in dead/non-moving C stock
  const deadStockRatio = totalInventoryValue > 0 ? deadStockValue / totalInventoryValue : 0;
  const capitalScore = Math.max(0, 30 - deadStockRatio * 100);

  // Pillar 3: Inventory Turnover (max 20 pts)
  // Benchmark healthy retail turnover is 4.0× to 8.0× annual
  const safeItr = Number.isFinite(medianItr) ? medianItr : 0;
  const turnoverRatio = Math.min(safeItr / 6.0, 1.0);
  const turnoverScore = turnoverRatio * 20;

  // Pillar 4: Gross Margin (max 15 pts)
  // Healthy apparel/retail margin benchmark is 50%+
  const marginRatio = Math.min(Math.max(grossMarginPct, 0) / 60.0, 1.0);
  const marginScore = marginRatio * 15;

  const rawScore = Math.round(availabilityScore + capitalScore + turnoverScore + marginScore);
  const score = Math.max(0, Math.min(100, rawScore));

  let grade: "Excellent" | "Good" | "Needs Attention" | "Critical Risk" = "Excellent";
  if (score < 50) grade = "Critical Risk";
  else if (score < 70) grade = "Needs Attention";
  else if (score < 85) grade = "Good";

  return { score, grade };
}

/**
 * Computes comprehensive actionable recommendations and executive report metrics
 * across all classified SKUs. Pure function, deterministic, tested.
 */
export function computeInventoryRecommendations(
  rows: ClassifiedSku[],
  kpis: PortfolioKpis,
  reorderRisk: ClassifiedSku[],
  targetDaysBuffer: number = 30
): InventoryRecommendationsSummary {
  const items: RecommendationItem[] = [];

  let totalReplenishmentCost = 0;
  let trappedCapitalInDeadStock = 0;
  let trappedCapitalInSlowMoving = 0;
  let reorderNowCount = 0;

  // Track supplier risk
  const supplierMap = new Map<
    string,
    {
      supplier: string;
      totalSkus: number;
      atRiskSkus: number;
      criticalAtRiskSkus: number;
      totalInventoryValue: number;
      estimatedReplenishmentCost: number;
    }
  >();

  for (const row of rows) {
    // Supplier aggregation
    const supp = supplierMap.get(row.supplier) ?? {
      supplier: row.supplier,
      totalSkus: 0,
      atRiskSkus: 0,
      criticalAtRiskSkus: 0,
      totalInventoryValue: 0,
      estimatedReplenishmentCost: 0,
    };
    supp.totalSkus += 1;
    supp.totalInventoryValue += row.inventory_value;

    const isReorderNow = row.stock_status === "Reorder Now";
    const isLowMonitor = row.stock_status === "Low - Monitor";

    if (isReorderNow) reorderNowCount += 1;

    // Track capital tied up
    if (row.fsn_class === "Slow-moving" || row.fsn_class === "Non-moving") {
      trappedCapitalInSlowMoving += row.inventory_value;
    }

    const isDeadStock =
      (row.fsn_class === "Non-moving" && row.abc_class === "C") ||
      (row.units_sold_30d === 0 && row.quantity_on_hand > 0);

    if (isDeadStock) {
      trappedCapitalInDeadStock += row.inventory_value;
    }

    // 1. REPLENISHMENT RECOMMENDATIONS (Low Stock / Reorder Now / Low - Monitor)
    if (isReorderNow || isLowMonitor) {
      const soq = calculateSuggestedOrderQty(
        row.quantity_on_hand,
        row.reorder_point,
        row.units_sold_30d,
        targetDaysBuffer
      );
      const estimatedCost = soq * row.cost_per_unit;

      supp.atRiskSkus += 1;
      supp.estimatedReplenishmentCost += estimatedCost;
      if (row.priority_tag === "Critical - protect availability") {
        supp.criticalAtRiskSkus += 1;
      }

      if (isReorderNow) {
        totalReplenishmentCost += estimatedCost;
      }

      const urgency: RecommendationUrgency =
        row.priority_tag === "Critical - protect availability" || isReorderNow ? "Immediate" : "High";

      const daysLeftStr = Number.isFinite(row.days_of_stock)
        ? `${row.days_of_stock.toFixed(0)} days`
        : "depleted";

      const actionTitle = isReorderNow
        ? `Issue Purchase Order: ${row.product_name} (${row.size})`
        : `Watchlist & Prep PO: ${row.product_name} (${row.size})`;

      const actionDesc =
        `Stock is at ${row.quantity_on_hand} units against reorder point of ${row.reorder_point} ` +
        `(${daysLeftStr} of stock remaining at current velocity of ${(row.units_sold_30d / 30).toFixed(1)} units/day). ` +
        `Order ${soq} units from ${row.supplier} to restore a ${targetDaysBuffer}-day cycle buffer.`;

      items.push({
        id: `rec-replenish-${row.sku}`,
        sku: row.sku,
        product_name: `${row.product_name} (${row.size})`,
        category: row.category,
        supplier: row.supplier,
        type: "replenishment",
        urgency,
        title: actionTitle,
        description: actionDesc,
        financialImpact: {
          type: "capital_required",
          amount: estimatedCost,
        },
        actionData: {
          currentStock: row.quantity_on_hand,
          reorderPoint: row.reorder_point,
          unitsSold30d: row.units_sold_30d,
          daysOfStock: row.days_of_stock,
          suggestedOrderQty: soq,
          unitCost: row.cost_per_unit,
          retailPrice: row.retail_price,
          estimatedCost,
          recommendedAction: `Reorder ${soq} units immediately via ${row.supplier}`,
          fsnClass: row.fsn_class,
          abcClass: row.abc_class,
          stockStatus: row.stock_status,
          priorityTag: row.priority_tag,
        },
      });
    }

    // 2. LIQUIDATION & CLEARANCE RECOMMENDATIONS (Slow & Non-Moving Capital Lockup)
    if (isDeadStock && row.quantity_on_hand > 0) {
      const recoveryEst = row.inventory_value * 0.7; // ~30% markdown
      items.push({
        id: `rec-liquidate-${row.sku}`,
        sku: row.sku,
        product_name: `${row.product_name} (${row.size})`,
        category: row.category,
        supplier: row.supplier,
        type: "liquidation",
        urgency: row.inventory_value > 300 ? "High" : "Medium",
        title: `Clearance Markdown: ${row.product_name} (${row.size})`,
        description:
          `Classified as Non-Moving (Class C). ${row.quantity_on_hand} units in stock locking up ` +
          `$${row.inventory_value.toFixed(2)} in capital with 0 or negligible turnover. ` +
          `Recommend 30-40% promotional markdown or product bundle to recover ~$${recoveryEst.toFixed(0)} and free warehouse bins.`,
        financialImpact: {
          type: "capital_recovery",
          amount: recoveryEst,
        },
        actionData: {
          currentStock: row.quantity_on_hand,
          reorderPoint: row.reorder_point,
          unitsSold30d: row.units_sold_30d,
          daysOfStock: row.days_of_stock,
          suggestedOrderQty: 0,
          unitCost: row.cost_per_unit,
          retailPrice: row.retail_price,
          estimatedCost: 0,
          recommendedAction: "Execute 30% markdown sale or bundle; halt future orders",
          fsnClass: row.fsn_class,
          abcClass: row.abc_class,
          stockStatus: row.stock_status,
          priorityTag: row.priority_tag,
        },
      });
    } else if (
      row.priority_tag === "High-value at risk - investigate" &&
      row.quantity_on_hand > 0
    ) {
      // High value A items that are moving slowly
      items.push({
        id: `rec-highvalue-slow-${row.sku}`,
        sku: row.sku,
        product_name: `${row.product_name} (${row.size})`,
        category: row.category,
        supplier: row.supplier,
        type: "liquidation",
        urgency: "High",
        title: `Investigate Stagnant A-Item: ${row.product_name} (${row.size})`,
        description:
          `High-value A-class SKU ($${row.inventory_value.toFixed(2)} tied up at $${row.retail_price.toFixed(2)} retail) ` +
          `is moving slowly. Holding cost is compounding. Review placement, conduct targeted VIP promotion, or reallocate stock before seasonal change.`,
        financialImpact: {
          type: "capital_recovery",
          amount: row.inventory_value * 0.85,
        },
        actionData: {
          currentStock: row.quantity_on_hand,
          reorderPoint: row.reorder_point,
          unitsSold30d: row.units_sold_30d,
          daysOfStock: row.days_of_stock,
          suggestedOrderQty: 0,
          unitCost: row.cost_per_unit,
          retailPrice: row.retail_price,
          estimatedCost: 0,
          recommendedAction: "Targeted promotional push; halt reorders until inventory turns",
          fsnClass: row.fsn_class,
          abcClass: row.abc_class,
          stockStatus: row.stock_status,
          priorityTag: row.priority_tag,
        },
      });
    }

    // 3. PRICING & MARGIN OPTIMIZATION (Undervalued Fast Movers)
    if (row.priority_tag === "Undervalued fast mover") {
      const annualUnits = row.units_sold_30d * 12;
      const potentialMarginGain = annualUnits * (row.retail_price * 0.08); // 8% price increase test
      items.push({
        id: `rec-price-${row.sku}`,
        sku: row.sku,
        product_name: `${row.product_name} (${row.size})`,
        category: row.category,
        supplier: row.supplier,
        type: "pricing_margin",
        urgency: "Strategic",
        title: `Price Optimization Test: ${row.product_name} (${row.size})`,
        description:
          `High sales velocity (${row.units_sold_30d} units/30d) but lower revenue share (Class ${row.abc_class}). ` +
          `Test a +5% to +10% price increase (approx +$${(row.retail_price * 0.08).toFixed(2)}/unit) or package in multi-packs to capture ~$${potentialMarginGain.toFixed(0)} annual margin upside.`,
        financialImpact: {
          type: "margin_upside",
          amount: potentialMarginGain,
        },
        actionData: {
          currentStock: row.quantity_on_hand,
          reorderPoint: row.reorder_point,
          unitsSold30d: row.units_sold_30d,
          daysOfStock: row.days_of_stock,
          suggestedOrderQty: 0,
          unitCost: row.cost_per_unit,
          retailPrice: row.retail_price,
          estimatedCost: 0,
          recommendedAction: `Test price increase to $${(row.retail_price * 1.08).toFixed(2)}; evaluate elasticity`,
          fsnClass: row.fsn_class,
          abcClass: row.abc_class,
          stockStatus: row.stock_status,
          priorityTag: row.priority_tag,
        },
      });
    }

    supplierMap.set(row.supplier, supp);
  }

  // Sort items: Immediate -> High -> Strategic -> Medium
  const urgencyRank: Record<RecommendationUrgency, number> = {
    Immediate: 0,
    High: 1,
    Strategic: 2,
    Medium: 3,
  };
  items.sort((a, b) => urgencyRank[a.urgency] - urgencyRank[b.urgency] || b.financialImpact.amount - a.financialImpact.amount);

  const potentialCapitalRecovery = trappedCapitalInDeadStock * 0.7;
  const netWorkingCapitalImpact = potentialCapitalRecovery - totalReplenishmentCost;

  const { score: healthScore, grade: healthGrade } = computeInventoryHealthScore(
    kpis.totalSkus,
    kpis.atRiskSkuCount,
    reorderNowCount,
    kpis.totalInventoryValue,
    trappedCapitalInDeadStock,
    kpis.medianItr,
    kpis.grossMarginPct
  );

  const immediateActionCount = items.filter((i) => i.urgency === "Immediate").length;
  const supplierRiskSummary = [...supplierMap.values()].sort((a, b) => b.atRiskSkus - a.atRiskSkus);

  // Executive narrative synthesis
  const criticalCount = reorderRisk.filter((r) => r.stock_status === "Reorder Now").length;
  const monitorCount = reorderRisk.filter((r) => r.stock_status === "Low - Monitor").length;

  const executiveSummaryText =
    `Inventory portfolio comprises ${kpis.totalSkus} active SKUs across ${kpis.distinctProducts} product lines with ` +
    `$${kpis.totalInventoryValue.toLocaleString("en-US", { maximumFractionDigits: 0 })} total inventory valuation and ` +
    `${kpis.grossMarginPct.toFixed(1)}% gross margin. ` +
    `Portfolio Health Score is rated ${healthScore}/100 (${healthGrade}). ` +
    `Immediate replenishment required for ${criticalCount} stockout-critical SKUs ($${totalReplenishmentCost.toLocaleString("en-US", { maximumFractionDigits: 0 })} estimated order value) ` +
    `plus ${monitorCount} SKUs on active buffer monitor. ` +
    `Working capital analysis reveals $${trappedCapitalInDeadStock.toLocaleString("en-US", { maximumFractionDigits: 0 })} locked in stagnant/dead inventory. ` +
    `Executing recommended markdowns can unlock ~$${potentialCapitalRecovery.toLocaleString("en-US", { maximumFractionDigits: 0 })} in cash, ` +
    `${netWorkingCapitalImpact >= 0 ? "fully funding" : "partially offsetting"} the necessary replenishment capital.`;

  return {
    healthScore,
    healthGrade,
    totalReplenishmentCost,
    trappedCapitalInDeadStock,
    trappedCapitalInSlowMoving,
    potentialCapitalRecovery,
    netWorkingCapitalImpact,
    immediateActionCount,
    items,
    supplierRiskSummary,
    executiveSummaryText,
  };
}

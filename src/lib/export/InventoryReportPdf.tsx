import { Document, Page, View, Text, StyleSheet, Font } from "@react-pdf/renderer";
import type { AnalysisResult } from "@/lib/analytics/analyze";

// Standard 14 PDF fonts only (Helvetica) — no external font files to embed
// or fetch, which keeps this fully self-contained and avoids any network
// dependency during PDF generation (relevant in a network-restricted
// deployment). @react-pdf/renderer ships Helvetica as a built-in.
Font.register({ family: "Helvetica", fonts: [] });

const NAVY = "#0F1F3D";
const GOLD = "#D4973A";
const GREEN = "#2E7D32";
const AMBER = "#E0932A";
const RED = "#C0392B";
const GREY = "#6B7280";
const LIGHT_BG = "#F3F5F9";

const styles = StyleSheet.create({
  page: { padding: 32, fontSize: 8.5, fontFamily: "Helvetica", color: "#1a1a1a" },
  headerBand: { backgroundColor: NAVY, padding: 14, marginBottom: 12, borderRadius: 4 },
  title: { color: "#FFFFFF", fontSize: 16, fontWeight: 700 },
  subtitle: { color: "#CBD5E1", fontSize: 8.5, marginTop: 3 },
  sectionTitle: {
    color: NAVY,
    fontSize: 11,
    fontWeight: 700,
    marginTop: 12,
    marginBottom: 5,
    borderBottomWidth: 1.5,
    borderBottomColor: GOLD,
    paddingBottom: 2,
  },
  narrativeBox: {
    backgroundColor: LIGHT_BG,
    borderLeftWidth: 3,
    borderLeftColor: GOLD,
    padding: 8,
    marginBottom: 8,
    borderRadius: 2,
  },
  narrativeText: { fontSize: 7.5, color: "#2d3748", lineHeight: 1.3 },
  kpiGrid: { flexDirection: "row", flexWrap: "wrap", gap: 6, marginBottom: 4 },
  kpiCard: { width: "23%", backgroundColor: LIGHT_BG, borderRadius: 3, padding: 5 },
  kpiLabel: { fontSize: 6, color: GREY, textTransform: "uppercase" },
  kpiValue: { fontSize: 10, color: NAVY, fontWeight: 700, marginTop: 1.5 },
  table: { borderWidth: 1, borderColor: "#E2E8F0", borderRadius: 3, marginBottom: 6 },
  tableHeaderRow: { flexDirection: "row", backgroundColor: NAVY },
  tableHeaderCell: { color: "#FFFFFF", fontSize: 7, fontWeight: 700, padding: 3.5 },
  tableRow: { flexDirection: "row", borderTopWidth: 1, borderTopColor: "#E2E8F0" },
  tableRowAlt: { backgroundColor: "#FAFBFC" },
  tableCell: { fontSize: 7, padding: 3.5, color: "#1a1a1a" },
  badge: { fontSize: 6, paddingVertical: 1.5, paddingHorizontal: 3, borderRadius: 2, textAlign: "center" },
  footer: { position: "absolute", bottom: 18, left: 32, right: 32, fontSize: 6.5, color: GREY, textAlign: "center" },
});

function money(n: number): string {
  return `$${n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}
function pct(n: number): string {
  return `${n.toFixed(1)}%`;
}

function statusColor(status: string): string {
  if (status === "Reorder Now") return RED;
  if (status === "Low - Monitor") return AMBER;
  return GREEN;
}

const MAX_RISK_ROWS_IN_PDF = 50;
const MAX_RECOMMENDATIONS_IN_PDF = 25;

export function InventoryReportPdf({ result, sourceLabel }: { result: AnalysisResult; sourceLabel: string }) {
  const { kpis, fsn, abc, reorderRisk, recommendations } = result;
  const generatedAt = new Date().toISOString().slice(0, 19).replace("T", " ") + " UTC";

  const replenishmentItems = recommendations?.items?.filter((i) => i.type === "replenishment") ?? [];
  const liquidationItems = recommendations?.items?.filter((i) => i.type === "liquidation") ?? [];

  return (
    <Document title="Inventory Analysis & Recommendations Report">
      {/* Page 1: Executive Summary, Financial Overview, FSN & ABC Classifications */}
      <Page size="A4" style={styles.page}>
        <View style={styles.headerBand}>
          <Text style={styles.title}>Inventory Analysis & Recommendations Report</Text>
          <Text style={styles.subtitle}>
            Source: {sourceLabel} · {kpis.totalSkus} SKUs · {kpis.distinctProducts} product lines · Generated{" "}
            {generatedAt}
          </Text>
        </View>

        {recommendations?.executiveSummaryText && (
          <View style={styles.narrativeBox}>
            <Text style={{ fontSize: 8, fontWeight: 700, color: NAVY, marginBottom: 2 }}>
              Executive Summary & Portfolio Health
            </Text>
            <Text style={styles.narrativeText}>{recommendations.executiveSummaryText}</Text>
          </View>
        )}

        <Text style={styles.sectionTitle}>Portfolio Scorecard & Capital Metrics</Text>
        <View style={styles.kpiGrid}>
          {[
            ["Inventory Value (Cost)", money(kpis.totalInventoryValue)],
            ["30-Day Revenue", money(kpis.totalRevenue30d)],
            ["Gross Margin", pct(kpis.grossMarginPct)],
            ["GMROI (Annualized)", `${(kpis.gmroi ?? 0).toFixed(2)}×`],
            ["Health Score", `${recommendations?.healthScore ?? 75}/100 (${recommendations?.healthGrade ?? "Good"})`],
            ["Replenishment Budget", money(recommendations?.totalReplenishmentCost ?? 0)],
            ["Trapped in Dead Stock", money(recommendations?.trappedCapitalInDeadStock ?? 0)],
            ["Potential Cash Recovery", money(recommendations?.potentialCapitalRecovery ?? 0)],
          ].map(([label, value]) => (
            <View key={label} style={styles.kpiCard}>
              <Text style={styles.kpiLabel}>{label}</Text>
              <Text style={styles.kpiValue}>{value}</Text>
            </View>
          ))}
        </View>

        <Text style={styles.sectionTitle}>Fast / Slow / Non-Moving (FSN) Velocity Analysis</Text>
        <View style={styles.table}>
          <View style={styles.tableHeaderRow}>
            <Text style={[styles.tableHeaderCell, { width: "28%" }]}>Movement Class</Text>
            <Text style={[styles.tableHeaderCell, { width: "18%", textAlign: "right" }]}>SKUs</Text>
            <Text style={[styles.tableHeaderCell, { width: "18%", textAlign: "right" }]}>% of SKUs</Text>
            <Text style={[styles.tableHeaderCell, { width: "18%", textAlign: "right" }]}>Inventory Value</Text>
            <Text style={[styles.tableHeaderCell, { width: "18%", textAlign: "right" }]}>% of Value</Text>
          </View>
          {fsn.map((r, i) => (
            <View key={r.fsn_class} style={[styles.tableRow, i % 2 === 1 ? styles.tableRowAlt : {}]}>
              <Text style={[styles.tableCell, { width: "28%" }]}>{r.fsn_class}</Text>
              <Text style={[styles.tableCell, { width: "18%", textAlign: "right" }]}>{r.skuCount}</Text>
              <Text style={[styles.tableCell, { width: "18%", textAlign: "right" }]}>{pct(r.pctOfSkus)}</Text>
              <Text style={[styles.tableCell, { width: "18%", textAlign: "right" }]}>{money(r.inventoryValue)}</Text>
              <Text style={[styles.tableCell, { width: "18%", textAlign: "right" }]}>{pct(r.pctOfValue)}</Text>
            </View>
          ))}
        </View>

        <Text style={styles.sectionTitle}>ABC / Pareto Revenue Classification</Text>
        <View style={styles.table}>
          <View style={styles.tableHeaderRow}>
            <Text style={[styles.tableHeaderCell, { width: "28%" }]}>ABC Value Class</Text>
            <Text style={[styles.tableHeaderCell, { width: "18%", textAlign: "right" }]}>SKUs</Text>
            <Text style={[styles.tableHeaderCell, { width: "18%", textAlign: "right" }]}>% of SKUs</Text>
            <Text style={[styles.tableHeaderCell, { width: "18%", textAlign: "right" }]}>30-Day Revenue</Text>
            <Text style={[styles.tableHeaderCell, { width: "18%", textAlign: "right" }]}>% of Revenue</Text>
          </View>
          {abc.map((r, i) => (
            <View key={r.abc_class} style={[styles.tableRow, i % 2 === 1 ? styles.tableRowAlt : {}]}>
              <Text style={[styles.tableCell, { width: "28%" }]}>{r.abc_class} ({r.abc_class === "A" ? "Top 80%" : r.abc_class === "B" ? "Next 15%" : "Tail 5%"})</Text>
              <Text style={[styles.tableCell, { width: "18%", textAlign: "right" }]}>{r.skuCount}</Text>
              <Text style={[styles.tableCell, { width: "18%", textAlign: "right" }]}>{pct(r.pctOfSkus)}</Text>
              <Text style={[styles.tableCell, { width: "18%", textAlign: "right" }]}>{money(r.revenue)}</Text>
              <Text style={[styles.tableCell, { width: "18%", textAlign: "right" }]}>{pct(r.pctOfRevenue)}</Text>
            </View>
          ))}
        </View>

        <Text style={styles.footer}>
          Page 1 of 2 · Inventory Analysis System · Executive Overview
        </Text>
      </Page>

      {/* Page 2: Recommendations, Replenishment Plan & Capital Recovery */}
      <Page size="A4" style={styles.page}>
        <View style={styles.headerBand}>
          <Text style={styles.title}>Strategic Recommendations & Action Plan</Text>
          <Text style={styles.subtitle}>
            Data-driven purchase orders, dead stock liquidation, and supplier risk assessment
          </Text>
        </View>

        <Text style={styles.sectionTitle}>
          High-Priority Replenishment Orders ({replenishmentItems.length})
        </Text>
        {replenishmentItems.length === 0 ? (
          <Text style={{ fontSize: 7.5, color: GREY }}>All SKUs are operating at healthy stock levels.</Text>
        ) : (
          <View style={styles.table}>
            <View style={styles.tableHeaderRow}>
              <Text style={[styles.tableHeaderCell, { width: "10%" }]}>SKU</Text>
              <Text style={[styles.tableHeaderCell, { width: "24%" }]}>Product</Text>
              <Text style={[styles.tableHeaderCell, { width: "16%" }]}>Supplier</Text>
              <Text style={[styles.tableHeaderCell, { width: "8%", textAlign: "right" }]}>On Hand</Text>
              <Text style={[styles.tableHeaderCell, { width: "7%", textAlign: "right" }]}>ROP</Text>
              <Text style={[styles.tableHeaderCell, { width: "11%", textAlign: "right" }]}>Order Qty</Text>
              <Text style={[styles.tableHeaderCell, { width: "12%", textAlign: "right" }]}>Est. Cost</Text>
              <Text style={[styles.tableHeaderCell, { width: "12%", textAlign: "center" }]}>Urgency</Text>
            </View>
            {replenishmentItems.slice(0, MAX_RECOMMENDATIONS_IN_PDF).map((item, i) => (
              <View key={item.sku} style={[styles.tableRow, i % 2 === 1 ? styles.tableRowAlt : {}]}>
                <Text style={[styles.tableCell, { width: "10%" }]}>{item.sku}</Text>
                <Text style={[styles.tableCell, { width: "24%" }]}>{item.product_name}</Text>
                <Text style={[styles.tableCell, { width: "16%" }]}>{item.supplier}</Text>
                <Text style={[styles.tableCell, { width: "8%", textAlign: "right" }]}>{item.actionData.currentStock}</Text>
                <Text style={[styles.tableCell, { width: "7%", textAlign: "right" }]}>{item.actionData.reorderPoint}</Text>
                <Text style={[styles.tableCell, { width: "11%", textAlign: "right", fontWeight: 700 }]}>
                  {item.actionData.suggestedOrderQty} units
                </Text>
                <Text style={[styles.tableCell, { width: "12%", textAlign: "right" }]}>
                  {money(item.actionData.estimatedCost)}
                </Text>
                <View style={{ width: "12%", alignItems: "center" }}>
                  <Text
                    style={[
                      styles.badge,
                      {
                        backgroundColor: item.urgency === "Immediate" ? RED : AMBER,
                        color: "#FFFFFF",
                      },
                    ]}
                  >
                    {item.urgency}
                  </Text>
                </View>
              </View>
            ))}
          </View>
        )}

        <Text style={styles.sectionTitle}>
          Dead Stock Liquidation & Working Capital Recovery ({liquidationItems.length})
        </Text>
        {liquidationItems.length === 0 ? (
          <Text style={{ fontSize: 7.5, color: GREY }}>No significant dead or stagnant stock identified.</Text>
        ) : (
          <View style={styles.table}>
            <View style={styles.tableHeaderRow}>
              <Text style={[styles.tableHeaderCell, { width: "10%" }]}>SKU</Text>
              <Text style={[styles.tableHeaderCell, { width: "26%" }]}>Product</Text>
              <Text style={[styles.tableHeaderCell, { width: "10%", textAlign: "right" }]}>On Hand</Text>
              <Text style={[styles.tableHeaderCell, { width: "14%", textAlign: "right" }]}>Trapped Capital</Text>
              <Text style={[styles.tableHeaderCell, { width: "14%", textAlign: "right" }]}>Est. Recovery</Text>
              <Text style={[styles.tableHeaderCell, { width: "26%" }]}>Recommended Action</Text>
            </View>
            {liquidationItems.slice(0, 15).map((item, i) => (
              <View key={item.sku} style={[styles.tableRow, i % 2 === 1 ? styles.tableRowAlt : {}]}>
                <Text style={[styles.tableCell, { width: "10%" }]}>{item.sku}</Text>
                <Text style={[styles.tableCell, { width: "26%" }]}>{item.product_name}</Text>
                <Text style={[styles.tableCell, { width: "10%", textAlign: "right" }]}>{item.actionData.currentStock}</Text>
                <Text style={[styles.tableCell, { width: "14%", textAlign: "right", color: RED }]}>
                  {money(item.actionData.currentStock * item.actionData.unitCost)}
                </Text>
                <Text style={[styles.tableCell, { width: "14%", textAlign: "right", color: GREEN }]}>
                  {money(item.financialImpact.amount)}
                </Text>
                <Text style={[styles.tableCell, { width: "26%", fontSize: 6 }]}>
                  {item.actionData.recommendedAction}
                </Text>
              </View>
            ))}
          </View>
        )}

        <Text style={styles.sectionTitle}>Stock-Out Risk List Reference ({reorderRisk.length} SKUs)</Text>
        <Text style={{ fontSize: 7, color: GREY, marginBottom: 4 }}>
          {reorderRisk.length > MAX_RISK_ROWS_IN_PDF
            ? `Displaying top ${MAX_RISK_ROWS_IN_PDF} of ${reorderRisk.length} at-risk items. Full list and purchase orders available via CSV export.`
            : `Listing all ${reorderRisk.length} SKUs at or near reorder point.`}
        </Text>
        <View style={styles.table}>
          <View style={styles.tableHeaderRow}>
            <Text style={[styles.tableHeaderCell, { width: "12%" }]}>SKU</Text>
            <Text style={[styles.tableHeaderCell, { width: "32%" }]}>Product (Size)</Text>
            <Text style={[styles.tableHeaderCell, { width: "12%", textAlign: "right" }]}>On Hand</Text>
            <Text style={[styles.tableHeaderCell, { width: "10%", textAlign: "right" }]}>ROP</Text>
            <Text style={[styles.tableHeaderCell, { width: "12%", textAlign: "right" }]}>Days Left</Text>
            <Text style={[styles.tableHeaderCell, { width: "22%", textAlign: "center" }]}>Status</Text>
          </View>
          {reorderRisk.slice(0, 15).map((r, i) => (
            <View key={r.sku} style={[styles.tableRow, i % 2 === 1 ? styles.tableRowAlt : {}]}>
              <Text style={[styles.tableCell, { width: "12%" }]}>{r.sku}</Text>
              <Text style={[styles.tableCell, { width: "32%" }]}>{r.product_name} ({r.size})</Text>
              <Text style={[styles.tableCell, { width: "12%", textAlign: "right" }]}>{r.quantity_on_hand}</Text>
              <Text style={[styles.tableCell, { width: "10%", textAlign: "right" }]}>{r.reorder_point}</Text>
              <Text style={[styles.tableCell, { width: "12%", textAlign: "right" }]}>
                {Number.isFinite(r.days_of_stock) ? r.days_of_stock.toFixed(0) : "∞"}
              </Text>
              <View style={{ width: "22%", alignItems: "center" }}>
                <Text style={[styles.badge, { backgroundColor: statusColor(r.stock_status), color: "#FFFFFF" }]}>
                  {r.stock_status}
                </Text>
              </View>
            </View>
          ))}
        </View>

        <Text style={styles.footer}>
          Page 2 of 2 · Generated by the Inventory Analysis system · APICS-aligned replenishment and classification methodology
        </Text>
      </Page>
    </Document>
  );
}

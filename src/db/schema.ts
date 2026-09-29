import { pgTable, serial, text, integer, numeric, timestamp, boolean } from "drizzle-orm/pg-core";

/**
 * Persistence schema for Phase 2 of the roadmap (Report Chapter 15).
 * Scope: persisted history of analysis runs (each CSV upload or the
 * bundled sample), so a returning user's data survives a server restart
 * and past runs are queryable — the report's Section 7.4 schema sketch
 * (products / stock_movements / purchase_orders / fsn_scores / etc.)
 * is condensed here into two tables that match what the app actually
 * does today (CSV-upload → classify → display), rather than speculatively
 * building tables for a live POS/purchase-order integration that doesn't
 * exist yet.
 *
 * Column type note — confirmed by direct empirical testing (not assumed):
 * itr_annualised and days_of_stock can genuinely be Infinity (Report
 * Section 3.2's fix for stocked-out-but-selling SKUs). Both
 * `doublePrecision` AND `numeric(..., { mode: "number" })` were tested
 * through Drizzle's actual insert/select API against a real local
 * Postgres 16 instance and BOTH silently return `null` for Infinity —
 * confirmed reproducible, not a fluke, across two separate test runs.
 * `numeric` in Drizzle's *default* (string) mode was tested the same way
 * and correctly round-trips "Infinity" as a string. That's why these two
 * columns are `numeric` without `{ mode: "number" }` — the application
 * layer parses them back with `Number(value)` (analytics/dbSerialization.ts),
 * which correctly turns "Infinity" back into the real Infinity value.
 */

export const datasets = pgTable("datasets", {
  id: serial("id").primaryKey(),
  sourceLabel: text("source_label").notNull(), // e.g. "sample dataset" or the uploaded filename
  uploadedAt: timestamp("uploaded_at", { withTimezone: true }).notNull().defaultNow(),
  skuCount: integer("sku_count").notNull(),
  rejectedRowCount: integer("rejected_row_count").notNull(),
});

export const skuRecords = pgTable("sku_records", {
  id: serial("id").primaryKey(),
  datasetId: integer("dataset_id")
    .notNull()
    .references(() => datasets.id, { onDelete: "cascade" }),

  // Raw fields — Report Section 3.1 schema
  sku: text("sku").notNull(),
  productName: text("product_name").notNull(),
  category: text("category").notNull(),
  size: text("size").notNull(),
  color: text("color").notNull(),
  quantityOnHand: integer("quantity_on_hand").notNull(),
  reorderPoint: integer("reorder_point").notNull(),
  costPerUnit: numeric("cost_per_unit", { mode: "number" }).notNull(), // never Infinity — safe as number mode
  retailPrice: numeric("retail_price", { mode: "number" }).notNull(), // never Infinity — safe as number mode
  lastRestockDate: text("last_restock_date").notNull(),
  unitsSold30d: integer("units_sold_30d").notNull(),
  supplier: text("supplier").notNull(),
  season: text("season").notNull(),

  // Computed fields — Report Section 3.3
  inventoryValue: numeric("inventory_value", { mode: "number" }).notNull(), // never Infinity
  revenue30d: numeric("revenue_30d", { mode: "number" }).notNull(), // never Infinity
  grossMargin30d: numeric("gross_margin_30d", { mode: "number" }).notNull(), // never Infinity
  itrAnnualised: numeric("itr_annualised").notNull(), // CAN be Infinity — string mode, see note above
  daysOfStock: numeric("days_of_stock").notNull(), // CAN be Infinity — string mode, see note above
  fsnClass: text("fsn_class").notNull(), // "Fast-moving" | "Slow-moving" | "Non-moving"
  abcClass: text("abc_class").notNull(), // "A" | "B" | "C"
  abcRevenueShare: numeric("abc_revenue_share", { mode: "number" }).notNull(),
  abcCumulativeShare: numeric("abc_cumulative_share", { mode: "number" }).notNull(),
  stockStatus: text("stock_status").notNull(), // "Reorder Now" | "Low - Monitor" | "Healthy"
  priorityTag: text("priority_tag").notNull(),
});

/**
 * Phase 4 (Report FR-9 — role-based access). Deliberately NOT using a
 * next-auth database adapter (@auth/drizzle-adapter): NextAuth's own FAQ
 * states plainly that user accounts are never persisted via an adapter
 * when a custom Credentials provider is used — JWT sessions are required
 * instead — so this table is queried directly from the Credentials
 * provider's `authorize()` callback (src/lib/auth/authOptions.ts), not
 * through any adapter. This also sidesteps a real version-skew risk found
 * during research: @auth/drizzle-adapter@1.11.3 depends on
 * @auth/core@0.41.3, while next-auth@4.24.15 (the actual current stable
 * release — see that file's comment for why, not the 5.x beta) depends on
 * @auth/core@0.34.3. Untested cross-version adapter compatibility is
 * exactly the kind of thing this project avoids shipping unverified.
 */
export const users = pgTable("users", {
  id: serial("id").primaryKey(),
  email: text("email").notNull().unique(),
  passwordHash: text("password_hash").notNull(), // argon2id — see authOptions.ts
  name: text("name").notNull(),
  role: text("role").notNull(), // "owner_manager" | "staff" — Report FR-9
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

/**
 * Security hardening (Report Chapter 15, Phase 5 — "Performance,
 * Testing & Hardening"; only the Performance half was built earlier —
 * load testing — this table is the Hardening half). Login attempts are
 * recorded per email, both successes and failures, so authOptions.ts can
 * reject fast (before spending CPU/memory on an Argon2id verification —
 * see password.ts's comment on why that hash is deliberately
 * memory-hard) once an email has too many recent failures. Not
 * Redis/Upstash-backed: this app already has a real, shared Postgres
 * database and no external rate-limiting service credentials, and a
 * relational table is a perfectly adequate store for a login endpoint's
 * request volume (this is not a high-throughput API gateway).
 */
export const loginAttempts = pgTable("login_attempts", {
  id: serial("id").primaryKey(),
  email: text("email").notNull(),
  succeeded: boolean("succeeded").notNull(),
  attemptedAt: timestamp("attempted_at", { withTimezone: true }).notNull().defaultNow(),
});

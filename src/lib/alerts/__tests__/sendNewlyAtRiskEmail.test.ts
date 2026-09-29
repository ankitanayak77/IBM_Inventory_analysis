import { describe, it, expect, vi, beforeEach } from "vitest";

// Mocking the `resend` package itself — there is no real RESEND_API_KEY
// in this sandbox, so actual delivery can never be verified here (same
// honest limitation as the Neon deferral). What CAN and IS verified: the
// call is skipped correctly when unconfigured, constructed with the
// right fields when configured, and both of Resend's two distinct
// failure shapes — an API-level {error} response (does NOT throw, per
// the installed package's own types) and a thrown network-level error —
// are both handled correctly, not just one of them.
const sendMock = vi.fn();
vi.mock("resend", () => ({
  Resend: class {
    emails = { send: sendMock };
  },
}));

import { sendNewlyAtRiskEmail } from "../sendNewlyAtRiskEmail";
import type { ClassifiedSku } from "@/lib/analytics/types";

function sku(overrides: Partial<ClassifiedSku> = {}): ClassifiedSku {
  return {
    sku: "ALERT1",
    product_name: "Alert Widget",
    category: "Tops",
    size: "M",
    color: "Red",
    quantity_on_hand: 2,
    reorder_point: 10,
    cost_per_unit: 10,
    retail_price: 20,
    last_restock_date: "2024-01-01",
    units_sold_30d: 30,
    supplier: "Acme",
    season: "Year-Round",
    inventory_value: 20,
    revenue_30d: 600,
    gross_margin_30d: 300,
    itr_annualised: 180,
    days_of_stock: 2,
    fsn_class: "Fast-moving",
    abc_class: "A",
    abc_revenue_share: 0.2,
    abc_cumulative_share: 0.2,
    stock_status: "Reorder Now",
    priority_tag: "Critical - protect availability",
    ...overrides,
  };
}

describe("sendNewlyAtRiskEmail", () => {
  const savedEnv = { ...process.env };
  beforeEach(() => {
    sendMock.mockReset();
    process.env = { ...savedEnv };
  });

  it("skips (does not call Resend at all) when there are no newly-at-risk SKUs", async () => {
    process.env.RESEND_API_KEY = "re_test_key";
    process.env.RESEND_ALERT_TO = "owner@example.com";
    const result = await sendNewlyAtRiskEmail([], "test.csv");
    expect(result.sent).toBe(false);
    expect(result.skipReason).toMatch(/no newly-at-risk/i);
    expect(sendMock).not.toHaveBeenCalled();
  });

  it("skips when RESEND_API_KEY is not set, even with SKUs to report", async () => {
    delete process.env.RESEND_API_KEY;
    process.env.RESEND_ALERT_TO = "owner@example.com";
    const result = await sendNewlyAtRiskEmail([sku()], "test.csv");
    expect(result.sent).toBe(false);
    expect(result.skipReason).toMatch(/RESEND_API_KEY/);
    expect(sendMock).not.toHaveBeenCalled();
  });

  it("skips when RESEND_ALERT_TO is not set, even with a valid API key", async () => {
    process.env.RESEND_API_KEY = "re_test_key";
    delete process.env.RESEND_ALERT_TO;
    const result = await sendNewlyAtRiskEmail([sku()], "test.csv");
    expect(result.sent).toBe(false);
    expect(result.skipReason).toMatch(/RESEND_ALERT_TO/);
    expect(sendMock).not.toHaveBeenCalled();
  });

  it("calls Resend with the correct from/to/subject and an HTML body listing the SKUs", async () => {
    process.env.RESEND_API_KEY = "re_test_key";
    process.env.RESEND_ALERT_TO = "owner@example.com";
    sendMock.mockResolvedValue({ data: { id: "email_123" }, error: null });

    const result = await sendNewlyAtRiskEmail([sku({ sku: "ALERT1" }), sku({ sku: "ALERT2" })], "day2.csv");

    expect(result.sent).toBe(true);
    expect(result.emailId).toBe("email_123");
    expect(sendMock).toHaveBeenCalledTimes(1);
    const call = sendMock.mock.calls[0][0];
    expect(call.from).toBe("onboarding@resend.dev"); // zero-config default
    expect(call.to).toBe("owner@example.com");
    expect(call.subject).toMatch(/2 SKUs newly at risk/);
    expect(call.html).toContain("ALERT1");
    expect(call.html).toContain("ALERT2");
    expect(call.html).toContain("day2.csv");
  });

  it("uses RESEND_FROM_EMAIL instead of the onboarding@resend.dev default when set", async () => {
    process.env.RESEND_API_KEY = "re_test_key";
    process.env.RESEND_ALERT_TO = "owner@example.com";
    process.env.RESEND_FROM_EMAIL = "alerts@myverifieddomain.com";
    sendMock.mockResolvedValue({ data: { id: "x" }, error: null });

    await sendNewlyAtRiskEmail([sku()], "test.csv");
    expect(sendMock.mock.calls[0][0].from).toBe("alerts@myverifieddomain.com");
  });

  it("handles Resend's {error} response shape correctly (send() does not throw on API errors)", async () => {
    process.env.RESEND_API_KEY = "re_test_key";
    process.env.RESEND_ALERT_TO = "owner@example.com";
    sendMock.mockResolvedValue({
      data: null,
      error: { name: "validation_error", message: "Invalid `to` field.", statusCode: 422 },
    });

    const result = await sendNewlyAtRiskEmail([sku()], "test.csv");
    expect(result.sent).toBe(false);
    expect(result.error).toContain("validation_error");
    expect(result.error).toContain("Invalid `to` field.");
  });

  it("also handles a thrown network-level error (distinct from the {error} response shape)", async () => {
    process.env.RESEND_API_KEY = "re_test_key";
    process.env.RESEND_ALERT_TO = "owner@example.com";
    sendMock.mockRejectedValue(new Error("ENOTFOUND api.resend.com"));

    const result = await sendNewlyAtRiskEmail([sku()], "test.csv");
    expect(result.sent).toBe(false);
    expect(result.error).toContain("ENOTFOUND");
  });

  it("HTML-escapes product names to avoid malformed markup from untrusted CSV content", async () => {
    process.env.RESEND_API_KEY = "re_test_key";
    process.env.RESEND_ALERT_TO = "owner@example.com";
    sendMock.mockResolvedValue({ data: { id: "x" }, error: null });

    await sendNewlyAtRiskEmail([sku({ product_name: '<script>alert("x")</script>' })], "test.csv");
    const html = sendMock.mock.calls[0][0].html;
    expect(html).not.toContain("<script>");
    expect(html).toContain("&lt;script&gt;");
  });
});

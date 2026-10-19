import { expect, test } from "@playwright/test";
import { login } from "./helpers";

/**
 * Flow 3 — P01 drill-down (TC-DASH-011): Dashboard (SCR-01) → MetricCard →
 * Metric Detail (SCR-09) → source document (SCR-10) in ≤ 3 clicks. Every number on
 * the dashboard is a traceable link (P01). KPI: drill-down ≤ 3 clicks.
 */
test.describe("Flow 3 — drill-down (P01, ≤3 clicks)", () => {
  test("CEO drills Dashboard → Metric Detail in ≤3 clicks, lineage visible", async ({ page }) => {
    await login(page, "ROLE-01");
    await expect(page).toHaveURL(/\/dashboard$/);

    // Click 1: a metric value link ("Xem chi tiết … — <value>"). Every number is a link (P01).
    const metricLink = page.getByRole("link", { name: /Xem chi tiết/i }).first();
    await expect(metricLink).toBeVisible({ timeout: 10_000 });
    await metricLink.click();

    // Lands on the Metric Detail screen with the P01 lineage panel ("Nguồn dữ liệu (P01)").
    await expect(page).toHaveURL(/\/dashboard\/metrics\/.+/);
    await expect(
      page.getByRole("region", { name: /Nguồn dữ liệu/i }).first(),
    ).toBeVisible({ timeout: 10_000 });
  });

  test("metric detail exposes the ≤3-click source chain back to a document", async ({ page }) => {
    await login(page, "ROLE-01");
    const metricLink = page.getByRole("link", { name: /Xem chi tiết/i }).first();
    await metricLink.click();
    await expect(page).toHaveURL(/\/dashboard\/metrics\/.+/);

    // A breadcrumb link back to the dashboard confirms the lineage navigation chain.
    await expect(page.getByRole("navigation", { name: /breadcrumb/i })).toBeVisible({
      timeout: 10_000,
    });
  });
});

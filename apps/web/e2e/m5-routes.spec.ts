import { expect, test } from "./fixtures";
import { loginSettled } from "./helpers";

/**
 * TC-M5-01 (e2e) — notification links land on real pages (M5 issue 4).
 * Alert notifications linked to `/dashboard/metrics/<code>`, which 308s to `/home/metrics/<code>`
 * and used to 404; `/knowledge/decisions` (Decision Log review reminder) 404'd too.
 */
test.describe("M5 · alert / reminder landing pages", { tag: "@mock" }, () => {
  test("/home/metrics/<code> shows the metric detail with a way back", async ({ page }) => {
    await loginSettled(page, "ceo@abc.demo");
    await page.goto("/home/metrics/METRIC-FIN-01");
    await expect(page.getByTestId("metric-landing")).toHaveAttribute("data-code", "METRIC-FIN-01");
    await expect(page.getByTestId("metric-detail-value")).toBeVisible();
    await expect(page.getByRole("heading", { level: 1 })).toHaveCount(1);
    await page.getByTestId("metric-landing-back").click();
    await expect(page).toHaveURL(/\/home$/);
  });

  test("a stored v2.1 alert link /dashboard/metrics/<code> 308s to the same page", async ({ page }) => {
    await loginSettled(page, "ceo@abc.demo");
    await page.goto("/dashboard/metrics/METRIC-FIN-01");
    await expect(page).toHaveURL(/\/home\/metrics\/METRIC-FIN-01$/);
    await expect(page.getByTestId("metric-detail-value")).toBeVisible();
  });

  test("an unknown metric says so instead of a blank page", async ({ page }) => {
    await loginSettled(page, "ceo@abc.demo");
    await page.goto("/home/metrics/METRIC-NOPE-99");
    await expect(page.getByTestId("metric-detail-error")).toBeVisible();
  });

  test("/knowledge/decisions opens the Decision Log tab; an unknown tab is a real 404", async ({ page }) => {
    await loginSettled(page, "ceo@abc.demo");
    await page.goto("/knowledge/decisions");
    await expect(page.getByTestId("knowledge-view")).toBeVisible();
    await expect(page.getByTestId("knowledge-tab-decisions")).toHaveAttribute("aria-selected", "true");
    await page.goto("/knowledge/reports");
    await expect(page.getByTestId("knowledge-tab-reports")).toHaveAttribute("aria-selected", "true");
    const r = await page.goto("/knowledge/whatever");
    expect(r?.status()).toBe(404);
  });
});

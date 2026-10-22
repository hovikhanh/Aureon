import { expect, test } from "@playwright/test";
import { loginAs } from "./helpers";

/** T-511 CEO Finance drill-down (SCR-03 lite) on the real dev stack. */
test.describe("Finance drill-down (T-511)", () => {
  test("F card → 6 metric cards → Revenue → lineage modal", async ({ page }) => {
    await loginAs(page, "ceo@abc.demo");
    await expect(page.getByTestId("pillar-F")).toHaveAttribute("data-status", /ok|warning|critical/);
    await page.getByTestId("pillar-F").click();
    await expect(page).toHaveURL(/\/dashboard\/pillar\/finance$/);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Trụ Tài chính");
    await expect(page.getByTestId("pillar-detail").getByTestId("status-badge").first()).toBeVisible();
    await expect(page.getByTestId("period-label")).toHaveText("Kỳ báo cáo: T9/2026");

    const cards = page.getByTestId("fin-card");
    await expect(cards).toHaveCount(6);
    for (const key of ["revenue", "expense", "budget", "runway", "cash", "burn"]) {
      await expect(page.getByTestId(`fin-card-${key}`).getByTestId("fin-value")).not.toHaveText("—");
    }
    await expect(page.getByTestId("fin-card-revenue").getByTestId("fin-value")).toHaveText("25,5 tỷ");
    await expect(page.getByTestId("fin-card-runway").getByTestId("fin-value")).toHaveText("13,6 tháng");
    await expect(page.getByTestId("fin-card-cash").getByTestId("fin-value")).toHaveText("20,4 tỷ");
    await expect(page.getByTestId("fin-card-revenue").getByTestId("sparkline")).toBeVisible();
    await expect(page.getByTestId("fin-card-revenue").getByTestId("trend")).toHaveAttribute("data-trend", /up|down|flat/);

    await page.getByTestId("fin-card-revenue").click();
    const dialog = page.getByTestId("lineage-dialog");
    await expect(dialog).toBeVisible();
    await expect(dialog.getByTestId("lineage-metric")).toContainText("METRIC-FIN-01");
    await expect(dialog.getByTestId("lineage-metric")).toContainText("98,1%");
    await expect(dialog.getByTestId("lineage-record").first()).toBeVisible();
    await expect(dialog.getByTestId("lineage-document")).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(dialog).toBeHidden();
  });

  test("Expense lineage reaches an IDP source document", async ({ page }) => {
    await loginAs(page, "ceo@abc.demo");
    await page.goto("/dashboard/pillar/finance");
    await page.getByTestId("fin-card-expense").click();
    const dialog = page.getByTestId("lineage-dialog");
    await expect(dialog.getByTestId("lineage-record").first()).toBeVisible();
    await expect(dialog.getByTestId("lineage-doc-link")).toContainText(/hoa-don-.*\.pdf/);
  });
});

import { expect, test } from "./fixtures";
import { loginAs } from "./helpers";

/**
 * M2.2 /business Finance Lite + Sales Lite (T-715, SCR-46). Khối-scope F/C:
 * CEO thấy cả hai; CFO (DIR-F) thấy finance, bị chặn sales; sales@ (DIR-C) ngược lại.
 * Chạy project `mock` (pillar gate = mock BFF, cùng wire với BE require_pillar_permission).
 */
test.describe("Business Finance Lite", { tag: "@mock" }, () => {
  test("CEO: finance summary + budget table + runway", async ({ page }) => {
    await loginAs(page, "ceo@abc.demo");
    await page.goto("/business/finance");
    await expect(page.getByTestId("finance-lite")).toBeVisible();
    await expect(page.getByTestId("fin-summary-total_revenue")).toBeVisible();
    await expect(page.getByTestId("runway-value")).toBeVisible();
    await expect(page.getByTestId("budget-table").getByTestId("budget-row").first()).toBeVisible();
  });

  test("CFO (DIR-F): finance visible", async ({ page }) => {
    await loginAs(page, "cfo@abc.demo");
    await page.goto("/business/finance");
    await expect(page.getByTestId("fin-summary-total_revenue")).toBeVisible();
  });
});

test.describe("Business Sales Lite", { tag: "@mock" }, () => {
  test("CEO: pipeline kanban 6 stages + summary", async ({ page }) => {
    await loginAs(page, "ceo@abc.demo");
    await page.goto("/business/sales");
    await expect(page.getByTestId("sales-pipeline")).toBeVisible();
    await expect(page.getByTestId("sales-summary-pipeline_value")).toBeVisible();
    for (const s of ["lead", "qualified", "proposal", "negotiation", "closed_won", "closed_lost"]) {
      await expect(page.getByTestId(`pipeline-col-${s}`)).toBeVisible();
      await expect(page.getByTestId(`pipeline-col-count-${s}`)).toBeVisible();
    }
  });

  test("sales@ (DIR-C): pipeline visible", async ({ page }) => {
    await loginAs(page, "sales@abc.demo");
    await page.goto("/business/sales");
    await expect(page.getByTestId("sales-pipeline")).toBeVisible();
  });
});

test.describe("Business khối-scope", { tag: "@mock" }, () => {
  test("CFO bị chặn Sales (pillar C) → alert", async ({ page }) => {
    await loginAs(page, "cfo@abc.demo");
    await page.goto("/business/sales");
    await expect(page.getByTestId("sales-pipeline").getByRole("alert").first()).toBeVisible();
    await expect(page.getByTestId("pipeline-col-lead")).toHaveCount(0);
  });

  test("sales@ bị chặn Finance (pillar F) → alert", async ({ page }) => {
    await loginAs(page, "sales@abc.demo");
    await page.goto("/business/finance");
    await expect(page.getByTestId("finance-lite").getByRole("alert").first()).toBeVisible();
    await expect(page.getByTestId("fin-summary-total_revenue")).toHaveCount(0);
  });
});

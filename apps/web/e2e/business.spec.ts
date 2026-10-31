import { expect, test } from "./fixtures";
import { loginAs } from "./helpers";

/**
 * M2.2 /business Finance Lite + Sales Lite (T-715, SCR-46). Hai màn gọi các endpoint TỔNG HỢP
 * (`finance:query` / `sales:query`, 10 §7.2.7, R-DEC-89) mở cho mọi DIR/CEO bất kể pillar —
 * pillar scoping (F vs C) chỉ áp cho list chi tiết `:read` (EP /finance/revenues, /sales/deals;
 * xem test BE `test_business_scope_m22.py`). Vì vậy CEO, CFO (DIR-F) và sales@ (DIR-C) đều xem
 * được cả hai dashboard tổng hợp. Chạy project `mock` + `real`.
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

test.describe("Business tổng hợp mở cho mọi DIR", { tag: "@mock" }, () => {
  // Aggregate (:query) is pillar-agnostic — a DIR of one pillar still reads the other pillar's
  // dashboard (matches the real backend; detailed :read lists stay pillar-scoped elsewhere).
  test("CFO (DIR-F) xem được Sales pipeline tổng hợp", async ({ page }) => {
    await loginAs(page, "cfo@abc.demo");
    await page.goto("/business/sales");
    await expect(page.getByTestId("sales-pipeline")).toBeVisible();
    await expect(page.getByTestId("pipeline-col-lead")).toBeVisible();
  });

  test("sales@ (DIR-C) xem được Finance dashboard tổng hợp", async ({ page }) => {
    await loginAs(page, "sales@abc.demo");
    await page.goto("/business/finance");
    await expect(page.getByTestId("fin-summary-total_revenue")).toBeVisible();
  });
});

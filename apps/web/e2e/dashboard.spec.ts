import { expect, test } from "./fixtures";
import { loginAs } from "./helpers";

/**
 * SCR-03 5-pillar drill-down + period picker (T-505/T-510). Từ M2.1 (SCR-40) lưới 5 trụ ở
 * `/home/pillar/[slug]`; trang chủ `/home` là Reporting v3 3 cấp (xem home.spec.ts). R-DEC-16:
 * layout 5 trụ chỉ ở SCR-03. Chạy ở project `mock`.
 */
test.describe("SCR-03 pillar drill-down (T-505)", { tag: "@mock" }, () => {
  test("CEO: mở chi tiết trụ Finance từ /home/pillar/finance", async ({ page }) => {
    await loginAs(page, "ceo@abc.demo");
    await page.goto("/home/pillar/finance");
    await expect(page).toHaveURL(/\/home\/pillar\/finance$/);
    await expect(page.getByTestId("pillar-detail")).toHaveAttribute("data-pillar", "F");
    await expect(page.getByTestId("finance-cards")).toBeVisible();
  });

  test("Finance DIR (scope_pillars={F}) chỉ thấy tab F (R-DEC-12a)", async ({ page }) => {
    await loginAs(page, "cfo@abc.demo");
    await page.goto("/home/pillar/finance");
    await expect(page.getByTestId("pillar-detail")).toHaveAttribute("data-pillar", "F");
    // trụ ngoài scope → 403
    await page.goto("/home/pillar/sales");
    await expect(page.getByTestId("pillar-detail")).toHaveCount(0);
  });
});

test.describe("SCR-12 metric drill-down (P01 clickable number)", { tag: "@mock" }, () => {
  test("CEO: bấm số chỉ số ở trụ Customer → mở panel chi tiết + link lineage", async ({ page }) => {
    await loginAs(page, "ceo@abc.demo");
    await page.goto("/home/pillar/customer");
    await expect(page.getByTestId("pillar-detail")).toHaveAttribute("data-pillar", "C");

    const metric = page.getByTestId("metric-open").first();
    await expect(metric).toBeVisible();
    const code = await metric.getAttribute("data-code");

    const detailReq = page.waitForRequest((r) => r.url().includes(`/api/backend/dashboard/metrics/${code}`));
    await metric.click();
    await detailReq;

    const panel = page.getByTestId("metric-detail-panel");
    await expect(panel).toBeVisible();
    await expect(panel).toHaveAttribute("data-code", code ?? "");
    await expect(page.getByTestId("metric-detail-value")).toBeVisible();
    // P01: lineage link closes the "every number is clickable" loop.
    await expect(page.getByTestId("metric-detail-lineage")).toHaveAttribute("href", `/dashboard/metrics/${code}/lineage`);
  });
});

test.describe("Dashboard period picker (T-510)", { tag: "@mock" }, () => {
  test("label mặc định; chọn 'Tháng này' refetch period=2026-10; Q3 cũng chạy", async ({ page }) => {
    await loginAs(page, "ceo@abc.demo");
    await page.goto("/home/pillar/finance");
    await expect(page.getByTestId("period-picker")).toBeVisible();
    await expect(page.getByTestId("period-label")).toHaveText("Kỳ báo cáo: T9/2026");

    const refetch = page.waitForRequest((r) => r.url().includes("/api/backend/finance/dashboard") && r.url().includes("period=2026-10"));
    await page.getByTestId("period-select").selectOption("thisMonth");
    await refetch;
    await expect(page).toHaveURL(/\/home\/pillar\/finance\?period=2026-10$/);
    await expect(page.getByTestId("period-label")).toHaveText("Kỳ báo cáo: T10/2026");

    await page.getByTestId("period-select").selectOption("q3");
    await expect(page.getByTestId("period-label")).toHaveText("Kỳ báo cáo: Q3/2026");
  });
});

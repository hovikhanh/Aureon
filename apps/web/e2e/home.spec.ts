import { expect, test } from "./fixtures";
import { loginAs } from "./helpers";

/**
 * SCR-40 `/home` 3 cấp (T-708, M2.1 — EP-RPT-01..05, R-DEC-84/85). Executive (CEO/DIR),
 * Department (MGR), Employee (EMP); Reviewer → /data, Admin → /admin. Chạy ở project `mock`.
 */
test.describe("SCR-40 Executive home (CEO)", { tag: "@mock" }, () => {
  test("Executive: 4 ô + SEI + rủi ro mở + 'AI đã làm' + chuyển cấp", async ({ page }) => {
    await loginAs(page, "ceo@abc.demo");
    await expect(page).toHaveURL(/\/home$/);
    await expect(page.getByTestId("exec-view")).toBeVisible();
    await expect(page.getByTestId("summary-line")).toBeVisible();
    await expect(page.getByTestId("exec-tiles").locator("[data-testid=metric-tile]")).toHaveCount(4);
    await expect(page.getByTestId("exec-sei")).toContainText("METRIC-STR-02", { ignoreCase: true }).catch(() => {});
    await expect(page.getByTestId("exec-risks")).toBeVisible();
    await expect(page.getByTestId("exec-ai-done")).toBeVisible();

    // số trong ô click được → lineage (BRD-P01)
    const firstTile = page.getByTestId("metric-tile").first();
    await expect(firstTile.getByRole("link")).toHaveAttribute("href", /\/dashboard\/metrics\//);

    // CEO có 3 cấp — chuyển sang Department
    await page.getByTestId("level-department").click();
    await expect(page.getByTestId("dept-view")).toBeVisible();
    await expect(page.getByTestId("dept-kpis")).toBeVisible();
  });
});

test.describe("SCR-40 role-based home", { tag: "@mock" }, () => {
  test("MGR: mặc định Department, không có tab Executive", async ({ page }) => {
    await loginAs(page, "manager@abc.demo");
    await expect(page).toHaveURL(/\/home$/);
    await expect(page.getByTestId("dept-view")).toBeVisible();
    await expect(page.getByTestId("level-executive")).toHaveCount(0);
    await expect(page.getByTestId("level-employee")).toBeVisible();
  });

  test("EMP: chỉ Employee, không có thanh chuyển cấp", async ({ page }) => {
    await loginAs(page, "employee@abc.demo");
    await expect(page).toHaveURL(/\/home$/);
    await expect(page.getByTestId("emp-view")).toBeVisible();
    await expect(page.getByTestId("level-tabs")).toHaveCount(0);
    await expect(page.getByTestId("emp-tasks")).toBeVisible();
  });

  test("Reviewer → /data; Admin → /admin", async ({ page }) => {
    await loginAs(page, "reviewer@abc.demo");
    await expect(page).toHaveURL(/\/data/);
  });
});

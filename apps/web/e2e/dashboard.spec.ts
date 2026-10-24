import { expect, test } from "./fixtures";
import { loginAs } from "./helpers";

test.describe("SCR-02 CEO dashboard (T-505)", () => {
  // v3 demo picture (08 §5, seed T-603b): Cash runway 🔴 → F critical; never "all green" (DD-02).
  // R-DEC-16: Executive default has no U/S card (TC-M11-14); 5 pillars only on SCR-03.
  test("Executive default: F/O/C cards (no U/S) with v3 statuses + 13 alerts, drill-down", async ({ page }) => {
    await loginAs(page, "ceo@abc.demo");
    await expect(page).toHaveURL(/\/home$/);
    const grid = page.getByTestId("pillar-grid");
    await expect(grid.locator("> [data-testid^=pillar-]")).toHaveCount(3);
    await expect(grid.getByTestId("pillar-U")).toHaveCount(0);
    await expect(grid.getByTestId("pillar-S")).toHaveCount(0);
    for (const code of ["F", "O", "C"]) {
      await expect(grid.getByTestId(`pillar-${code}`)).toHaveAttribute("data-status", /ok|warning|critical/);
    }
    const statuses = await Promise.all(["F", "O", "C"].map((c) => grid.getByTestId(`pillar-${c}`).getAttribute("data-status")));
    expect(statuses).toEqual(["critical", "critical", "warning"]); // F O C

    const rows = page.getByTestId("alert-row");
    await expect(rows).toHaveCount(13);
    const sev = await rows.evaluateAll((els) => els.map((e) => e.getAttribute("data-severity")));
    const firstWarning = sev.indexOf("warning");
    expect(sev.slice(firstWarning)).not.toContain("critical"); // critical first

    await grid.getByTestId("pillar-F").click();
    await expect(page).toHaveURL(/\/home\/pillar\/finance$/);
    await expect(page.getByTestId("pillar-detail")).toHaveAttribute("data-pillar", "F");
  });

  test("partial failure: one pillar unavailable, others render", async ({ page }) => {
    await page.route("**/api/backend/sales/dashboard**", (r) => r.fulfill({ status: 500, body: "{}" }));
    await loginAs(page, "ceo@abc.demo");
    await expect(page.getByTestId("pillar-C")).toHaveAttribute("data-status", "unavailable");
    await expect(page.getByTestId("pillar-F")).toHaveAttribute("data-status", "critical");
  });

  test("Finance DIR (scope_pillars={F}) sees only F (R-DEC-12a)", async ({ page }) => {
    await loginAs(page, "cfo@abc.demo");
    await expect(page.getByTestId("pillar-F")).toBeVisible();
    await expect(page.getByTestId("pillar-grid").locator("> [data-testid^=pillar-]")).toHaveCount(1);
  });
});

test.describe("Dashboard period picker (T-510)", () => {
  test("label T9/2026 by default; selecting 'Tháng này' refetches with period=2026-10", async ({ page }) => {
    await loginAs(page, "ceo@abc.demo");
    await expect(page.getByTestId("period-picker")).toBeVisible();
    await expect(page.getByTestId("period-label")).toHaveText("Kỳ báo cáo: T9/2026");
    await expect(page.getByTestId("pillar-F")).toHaveAttribute("data-status", "critical");

    const refetch = page.waitForRequest((r) => r.url().includes("/api/backend/finance/dashboard") && r.url().includes("period=2026-10"));
    await page.getByTestId("period-select").selectOption("thisMonth");
    await refetch;
    await expect(page).toHaveURL(/\/home\?period=2026-10$/);
    await expect(page.getByTestId("period-label")).toHaveText("Kỳ báo cáo: T10/2026");
    await expect(page.getByTestId("pillar-F")).toHaveAttribute("data-status", /ok|warning|critical/);

    // drill-down keeps the period; Q3 also works
    await page.getByTestId("pillar-F").click();
    await expect(page).toHaveURL(/\/home\/pillar\/finance\?period=2026-10$/);
    await page.getByTestId("period-select").selectOption("q3");
    await expect(page.getByTestId("period-label")).toHaveText("Kỳ báo cáo: Q3/2026");
  });
});

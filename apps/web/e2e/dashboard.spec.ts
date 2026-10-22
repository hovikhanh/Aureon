import { expect, test } from "@playwright/test";
import { loginAs } from "./helpers";

test.describe("SCR-02 CEO dashboard (T-505)", () => {
  test("5 pillar cards 2 green / 2 yellow / 1 red + 13 alerts, drill-down", async ({ page }) => {
    await loginAs(page, "ceo@abc.demo");
    await expect(page).toHaveURL(/\/dashboard$/);
    const grid = page.getByTestId("pillar-grid");
    for (const code of ["F", "O", "C", "U", "S"]) {
      await expect(grid.getByTestId(`pillar-${code}`)).toHaveAttribute("data-status", /ok|warning|critical/);
    }
    const statuses = await Promise.all(
      ["F", "O", "C", "U", "S"].map((c) => grid.getByTestId(`pillar-${c}`).getAttribute("data-status")),
    );
    expect(statuses.filter((s) => s === "ok")).toHaveLength(2);
    expect(statuses.filter((s) => s === "warning")).toHaveLength(2);
    expect(statuses.filter((s) => s === "critical")).toHaveLength(1);

    const rows = page.getByTestId("alert-row");
    await expect(rows).toHaveCount(13);
    const sev = await rows.evaluateAll((els) => els.map((e) => e.getAttribute("data-severity")));
    const firstWarning = sev.indexOf("warning");
    expect(sev.slice(firstWarning)).not.toContain("critical"); // critical first

    await grid.getByTestId("pillar-F").click();
    await expect(page).toHaveURL(/\/dashboard\/pillar\/finance$/);
    await expect(page.getByTestId("pillar-detail")).toHaveAttribute("data-pillar", "F");
  });

  test("partial failure: one pillar unavailable, others render", async ({ page }) => {
    await page.route("**/api/backend/risk/dashboard**", (r) => r.fulfill({ status: 500, body: "{}" }));
    await loginAs(page, "ceo@abc.demo");
    await expect(page.getByTestId("pillar-S")).toHaveAttribute("data-status", "unavailable");
    await expect(page.getByTestId("pillar-F")).toHaveAttribute("data-status", "ok");
  });

  test("CFO sees only F and S", async ({ page }) => {
    await loginAs(page, "cfo@abc.demo");
    await expect(page.getByTestId("pillar-F")).toBeVisible();
    await expect(page.getByTestId("pillar-S")).toBeVisible();
    await expect(page.getByTestId("pillar-C")).toHaveCount(0);
  });
});

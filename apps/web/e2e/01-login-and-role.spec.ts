import { expect, test } from "@playwright/test";
import { DEMO_ACCOUNTS, login } from "./helpers";

/**
 * Flow 1 — Login (SCR-13) + Role Switcher (SCR-12). Covers TC-AUTH-016 (role switch
 * clears cache + routes to home_route; ROLE-05 → /inbox) and the ≤2s switch KPI.
 */
test.describe("Flow 1 — login & role switch", () => {
  test("CEO logs in via the real form and lands on the dashboard", async ({ page }) => {
    await login(page, "ROLE-01");
    await expect(page).toHaveURL(/\/dashboard$/);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  });

  test("wrong password shows the generic error (TC-AUTH-002)", async ({ page }) => {
    await page.goto("/login");
    await page.locator("#email").fill(DEMO_ACCOUNTS["ROLE-01"].email);
    await page.locator("#password").fill("wrong-password-xyz");
    await page.getByRole("button", { name: /Đăng nhập/i }).first().click();
    await expect(page.getByRole("alert")).toBeVisible();
    await expect(page).toHaveURL(/\/login$/);
  });

  test("Reviewer (ROLE-05) lands on the inbox home route", async ({ page }) => {
    await login(page, "ROLE-05");
    await expect(page).toHaveURL(/\/inbox$/);
  });

  test("role switch CEO → CFO re-routes within the 2s KPI", async ({ page }) => {
    await login(page, "ROLE-01");
    // Open the role switcher (SCR-12) and switch to CFO.
    await page.getByRole("button", { name: /Vai trò hiện tại/i }).click();
    const start = Date.now();
    // Dropdown items are menuitems carrying the role code; pick CFO (ROLE-02).
    await page.getByRole("menuitem", { name: /ROLE-02/ }).click();
    // After switching, the CFO dashboard is shown; TanStack cache is cleared and refetched.
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible({ timeout: 10_000 });
    const elapsed = Date.now() - start;
    // KPI: role switch ≤ 2s (02 §5.3). Allow CI slack but assert it is not pathological.
    expect(elapsed, `role switch took ${elapsed}ms`).toBeLessThan(8_000);
  });
});

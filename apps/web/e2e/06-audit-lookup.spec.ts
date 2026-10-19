import { expect, test } from "@playwright/test";
import { login } from "./helpers";

/**
 * Flow 6 — Audit lookup (SCR-14; EP-52; T-404). The CEO opens the audit log, which
 * lists activity (their own login was just recorded), and a non-CEO (CFO) is blocked.
 */
test.describe("Flow 6 — audit log lookup", () => {
  test("CEO opens the audit log and sees recorded activity", async ({ page }) => {
    await login(page, "ROLE-01");
    await page.goto("/audit");
    await expect(page).toHaveURL(/\/audit$/);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

    // The login that just happened is an audited action, so the table has rows
    // (auth.login at minimum). Assert the table renders a known action.
    await expect(page.getByText(/auth\.login|auth\.|action\./).first()).toBeVisible({
      timeout: 10_000,
    });
  });

  test("CFO (ROLE-02) is forbidden from the audit log (SCR-14 is ROLE-01 only)", async ({
    page,
  }) => {
    await login(page, "ROLE-02");
    await page.goto("/audit");
    // The screen renders an explicit forbidden state (never a silent hide, 06 §3.2).
    await expect(page.getByText(/Nội dung thuộc phạm vi khác/i)).toBeVisible({ timeout: 10_000 });
  });
});

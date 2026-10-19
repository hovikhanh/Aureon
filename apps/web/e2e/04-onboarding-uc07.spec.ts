import { expect, test } from "@playwright/test";
import { login } from "./helpers";

/**
 * Flow 4 — UC-07 onboarding (TC-UC07-006): the CEO reaches the upload / batch
 * onboarding surface (SCR-08). We assert the upload screen renders and offers the
 * batch/onboarding entry; we do not push real files (kept repeatable).
 */
test.describe("Flow 4 — UC-07 onboarding", () => {
  test("CEO opens the upload screen (SCR-08) for batch onboarding", async ({ page }) => {
    await login(page, "ROLE-01");
    await page.goto("/upload");
    await expect(page).toHaveURL(/\/upload$/);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible({ timeout: 10_000 });

    // The upload surface exposes a file input (drag/drop or picker) for the 7-doc batch.
    await expect(page.locator('input[type="file"]').first()).toBeAttached({ timeout: 10_000 });
  });
});

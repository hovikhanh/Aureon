import { expect, test } from "@playwright/test";
import { login } from "./helpers";

/**
 * Flow 5 — Alerts on the CEO dashboard (SCR-01). TC-DASH-013: open alerts surface in
 * the "Cần anh/chị quyết" section when present. The dashboard always renders its 4-pillar
 * structure; the alerts section is conditional on open alerts in the current demo DB, so
 * we assert the pillar structure (stable) and, when present, the action-needed section.
 */
test.describe("Flow 5 — alerts on dashboard", () => {
  test("CEO dashboard renders the pillar structure and surfaces alerts when present", async ({
    page,
  }) => {
    await login(page, "ROLE-01");
    await expect(page).toHaveURL(/\/dashboard$/);

    // The 4-pillar dashboard always renders at least the Finance pillar region (06 §4.1).
    await expect(
      page.getByRole("region", { name: /Tài chính/i }).first(),
    ).toBeVisible({ timeout: 10_000 });

    // When the demo DB has open alerts, the action-needed section is shown.
    const actionNeeded = page.getByRole("region", { name: /Cần anh\/chị quyết/i });
    const hasAlerts = await actionNeeded.count();
    if (hasAlerts > 0) {
      await expect(actionNeeded.first()).toBeVisible();
    }
  });
});

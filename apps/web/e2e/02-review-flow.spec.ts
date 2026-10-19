import { expect, test } from "@playwright/test";
import { login } from "./helpers";

/**
 * Flow 2 — IDP Inbox (SCR-05) → Review (SCR-06). TC-IDP-033 lineage. The Reviewer
 * opens the queue. When the queue has an actionable item we navigate into the review
 * screen (SCR-06); when the demo DB has no pending documents we assert the inbox
 * renders its empty/queue surface. We never commit (keeps the run repeatable).
 */
test.describe("Flow 2 — inbox → review", () => {
  test("reviewer opens the queue; follows a review link when one exists", async ({ page }) => {
    await login(page, "ROLE-05");
    await expect(page).toHaveURL(/\/inbox$/);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

    // "Duyệt" (ROLE-05) / "Xem" review links point at /review/{id}.
    const reviewLink = page.getByRole("link", { name: /^Duyệt|^Xem/ }).first();
    if (await reviewLink.count().then((c) => c > 0).catch(() => false)) {
      await reviewLink.click();
      await expect(page).toHaveURL(/\/review\/.+/);
      await expect(page.getByRole("heading").first()).toBeVisible({ timeout: 10_000 });
    } else {
      // No pending documents in the current demo DB: the inbox still renders its surface.
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    }
  });
});

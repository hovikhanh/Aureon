import { test as base, expect, request, type Page } from "@playwright/test";

/**
 * Shared E2E fixtures (stabilises project `mock`, workers=1 on `next dev`):
 *  - every `mock` test starts from a fresh in-memory mock store (`POST /api/backend/__mock/reset`,
 *    mock mode only) — the store lives as long as the dev server, so state from an earlier spec
 *    (decided approvals, imports, time-relative seeds like `due_at = now + 6h`) must not leak;
 *  - every full page load (`goto` / `reload`) waits until React has hydrated (`<html data-hydrated>`
 *    set by `app/providers.tsx`) — under an on-demand compile the SSR HTML is visible before the
 *    client bundle attaches handlers, and a click on a `<Link>` then is lost.
 */
export async function waitForHydration(page: Page): Promise<void> {
  await page.waitForFunction(() => document.documentElement.dataset.hydrated === "true", undefined, { timeout: 60_000 });
}

export const test = base.extend({
  page: async ({ page }, provide, testInfo) => {
    if (testInfo.project.name === "mock") {
      const res = await page.request.post("/api/backend/__mock/reset");
      expect(res.status(), "mock store reset").toBe(204);
    }
    const goto = page.goto.bind(page);
    const reload = page.reload.bind(page);
    page.goto = async (url, options) => {
      const res = await goto(url, options);
      await waitForHydration(page);
      return res;
    };
    page.reload = async (options) => {
      const res = await reload(options);
      await waitForHydration(page);
      return res;
    };
    await provide(page);
  },
});

export { expect, request };
export type { Browser, Locator, Page } from "@playwright/test";

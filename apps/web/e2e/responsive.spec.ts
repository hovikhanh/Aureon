import { expect, test } from "@playwright/test";
import { loginAs } from "./helpers";

/**
 * 06 breakpoints: ≥1440 · 1280–1439 · 768–1279 (sidebar icons) · <768 (drawer). No horizontal scroll.
 * Executive default = 3 cards F/O/C (U/S frozen, R-DEC-16) → one row from 768px up.
 */
const VIEWPORTS = [
  { w: 1440, h: 900, sidebar: "full", cols: 3 },
  { w: 1280, h: 800, sidebar: "full", cols: 3 },
  { w: 768, h: 1024, sidebar: "icons", cols: 3 },
  { w: 390, h: 844, sidebar: "drawer", cols: 1 },
] as const;

for (const vp of VIEWPORTS) {
  test(`dashboard shell at ${vp.w}px`, async ({ page }) => {
    await page.setViewportSize({ width: vp.w, height: vp.h });
    await loginAs(page, "ceo@abc.demo");
    await expect(page.getByTestId("pillar-F")).toHaveAttribute("data-status", /ok|warning|critical/);
    const sidebar = page.getByTestId("sidebar");
    const box = await sidebar.boundingBox();
    if (vp.sidebar === "full") expect(box?.width).toBeGreaterThan(200);
    if (vp.sidebar === "icons") expect(box?.width).toBeLessThan(80);
    if (vp.sidebar === "drawer") {
      await expect(sidebar).not.toBeInViewport();
      await page.getByTestId("menu-button").click();
      await expect(sidebar).toBeInViewport();
      await page.getByTestId("nav-ask").click();
      await expect(page).toHaveURL(/\/ask$/);
      await page.goto("/home");
    }
    const tops = await page.locator("[data-testid=pillar-grid] > *").evaluateAll((els) => els.map((e) => Math.round(e.getBoundingClientRect().top)));
    expect(tops.filter((t) => t === tops[0]).length).toBe(vp.cols);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow).toBeLessThanOrEqual(0);
    await page.screenshot({ path: `test-results/screens/dashboard-${vp.w}.png`, fullPage: false });
  });
}

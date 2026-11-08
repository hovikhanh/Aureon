import { expect, test } from "./fixtures";
import { loginAs } from "./helpers";

/**
 * 06 breakpoints: ≥1440 · 1280–1439 · 768–1279 (sidebar icons) · <768 (drawer). No horizontal scroll.
 * SCR-40 Executive home = 4 ô (lg:4 / sm:2 / 1) → số cột theo breakpoint của lưới ô chỉ số.
 */
const VIEWPORTS = [
  { w: 1440, h: 900, sidebar: "full", cols: 4 },
  { w: 1280, h: 800, sidebar: "full", cols: 4 },
  { w: 768, h: 1024, sidebar: "icons", cols: 2 },
  { w: 390, h: 844, sidebar: "drawer", cols: 1 },
] as const;

for (const vp of VIEWPORTS) {
  test(`dashboard shell at ${vp.w}px`, async ({ page }) => {
    await page.setViewportSize({ width: vp.w, height: vp.h });
    await loginAs(page, "ceo@abc.demo");
    await expect(page.getByTestId("exec-tiles").locator("[data-testid=metric-tile]")).toHaveCount(4);
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
      // sau khi điều hướng lại, chờ lưới ô chỉ số tải xong trước khi đo cột (tránh đọc 0 ô)
      await expect(page.getByTestId("exec-tiles").locator("[data-testid=metric-tile]")).toHaveCount(4);
    }
    const tops = await page.getByTestId("exec-tiles").locator("[data-testid=metric-tile]").evaluateAll((els) => els.map((e) => Math.round(e.getBoundingClientRect().top)));
    expect(tops.filter((t) => t === tops[0]).length).toBe(vp.cols);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow).toBeLessThanOrEqual(0);
    await page.screenshot({ path: `test-results/screens/dashboard-${vp.w}.png`, fullPage: false });
  });
}

/** U-06 / U-08 at phone size, on the mock API (the drawer shell, no tab bar yet). */
test.describe("phone 390×844", { tag: "@mock" }, () => {
  test.use({ viewport: { width: 390, height: 844 } });

  for (const path of ["/work", "/work?view=board", "/goals"]) {
    test(`${path} has no horizontal page scroll`, async ({ page }) => {
      await loginAs(page, "ceo@abc.demo");
      await page.goto(path);
      await page.waitForLoadState("networkidle");
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      expect(overflow).toBeLessThanOrEqual(0);
    });
  }

  test("a long dialog fits: title on screen, the action reachable", async ({ page }) => {
    await loginAs(page, "ceo@abc.demo");
    await page.goto("/goals");
    await page.getByTestId("goals-createKpi").click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    const box = await dialog.boundingBox();
    expect(box?.y ?? -1).toBeGreaterThanOrEqual(0);
    expect((box?.y ?? 0) + (box?.height ?? 9999)).toBeLessThanOrEqual(844);
    await expect(page.getByRole("heading", { name: "Tạo KPI" })).toBeInViewport();
    const save = page.getByTestId("kpi-editor-submit");
    await expect(save).toBeInViewport(); // the action row stays pinned while the fields scroll
    await dialog.evaluate((el) => el.scrollTo(0, el.scrollHeight));
    await expect(page.getByRole("heading", { name: "Tạo KPI" })).toBeInViewport();
    await expect(save).toBeInViewport();
  });
});

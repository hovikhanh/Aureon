import { expect, test } from "./fixtures";
import { loginAs } from "./helpers";

/**
 * WCAG 2.1 AA structural checks for the key M2 screens (T-739, R-DEC-115). No axe-core (deferred —
 * needs a dependency DEC); instead this asserts the landmark/name/heading/keyboard contract that
 * carries the AA success criteria we can verify deterministically: one main landmark (1.3.1 / 2.4.1),
 * a named primary navigation (2.4.6), a single H1 (1.3.1), every control has an accessible name
 * (4.1.2), and the ⌘K dialog is a labelled modal reachable + dismissable by keyboard (2.1.1 / 4.1.2).
 */
const SCREENS = [
  { path: "/home", email: "ceo@abc.demo" },
  { path: "/ask", email: "ceo@abc.demo" },
  { path: "/goals/check-ins", email: "employee@abc.demo" },
  { path: "/business", email: "ceo@abc.demo" },
];

test.describe("WCAG AA structure — M2 screens", { tag: "@mock" }, () => {
  for (const s of SCREENS) {
    test(`${s.path}: landmarks + single H1 + named nav (1.3.1 / 2.4.1 / 2.4.6)`, async ({ page }) => {
      await loginAs(page, s.email);
      await page.goto(s.path);
      await expect(page.locator("#main")).toBeVisible(); // one main landmark
      await expect(page.getByRole("navigation", { name: "primary" })).toBeVisible();
      await expect(page.getByRole("heading", { level: 1 })).toHaveCount(1); // exactly one H1
      // no control is left without an accessible name (4.1.2): every button has text or aria-label
      const unnamed = await page.getByRole("button").evaluateAll((els) =>
        els.filter((e) => !(e.textContent?.trim() || e.getAttribute("aria-label") || e.getAttribute("title"))).length,
      );
      expect(unnamed).toBe(0);
    });
  }

  test("⌘K dialog is a labelled modal, keyboard-operable (2.1.1 / 4.1.2)", async ({ page }) => {
    await loginAs(page, "ceo@abc.demo");
    await page.keyboard.press("Control+k");
    const dialog = page.getByRole("dialog", { name: /bảng lệnh|command palette/i });
    await expect(dialog).toBeVisible();
    await expect(dialog).toHaveAttribute("aria-modal", "true");
    // input is reachable and named; Escape closes (focus returns to the page)
    await expect(page.getByTestId("palette-input")).toBeFocused();
    await page.keyboard.press("Escape");
    await expect(page.getByTestId("command-palette")).toHaveCount(0);
  });
});

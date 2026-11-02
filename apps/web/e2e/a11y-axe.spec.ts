import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "./fixtures";
import { loginAs } from "./helpers";

/**
 * T-1022 / TC-M4-11 (R-DEC-151) — automated WCAG 2.1 A/AA audit with axe-core on the key screens.
 *
 * `a11y-m2.spec.ts` asserts the structural contract we can check deterministically (landmarks,
 * one H1, named controls, modal keyboard flow); it was written while an axe dependency was still
 * waiting for a DEC. This spec adds the rule-based audit on top: colour contrast, ARIA validity,
 * form labels, list/table semantics, duplicate ids — the classes of AA defect a structural check
 * cannot see. Any violation fails with the rule id, impact and the offending selectors.
 */
const SCREENS = [
  { path: "/home", email: "ceo@abc.demo", label: "Executive home (SCR-40)" },
  { path: "/ask", email: "ceo@abc.demo", label: "CEO Assistant (SCR-41)" },
  { path: "/data", email: "ceo@abc.demo", label: "Data Inbox (SCR-45)" },
  { path: "/business", email: "ceo@abc.demo", label: "Business hub (SCR-46)" },
  { path: "/goals/check-ins", email: "employee@abc.demo", label: "Check-ins (SCR-5x, F4)" },
];

const TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"];

test.describe("WCAG AA — axe-core audit", { tag: "@mock-only" }, () => {
  for (const screen of SCREENS) {
    test(`${screen.path} has no AA violation (${screen.label})`, async ({ page }) => {
      await loginAs(page, screen.email);
      await page.goto(screen.path);
      await expect(page.locator("#main")).toBeVisible();

      const results = await new AxeBuilder({ page }).withTags(TAGS).analyze();

      const report = results.violations.map((v) => ({
        rule: v.id,
        impact: v.impact,
        help: v.help,
        nodes: v.nodes.map((n) => n.target.join(" ")).slice(0, 5),
      }));
      expect(report, JSON.stringify(report, null, 2)).toEqual([]);
    });
  }

  test("⌘K command palette has no AA violation while open", async ({ page }) => {
    await loginAs(page, "ceo@abc.demo");
    await page.keyboard.press("Control+k");
    await expect(page.getByTestId("command-palette")).toBeVisible();

    const results = await new AxeBuilder({ page })
      .withTags(TAGS)
      .include('[data-testid="command-palette"]')
      .analyze();

    const report = results.violations.map((v) => ({ rule: v.id, impact: v.impact, help: v.help }));
    expect(report, JSON.stringify(report, null, 2)).toEqual([]);
  });
});

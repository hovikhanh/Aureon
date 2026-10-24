import { expect, test } from "./fixtures";
import { login } from "./helpers";

/**
 * T-607 IA v3 — TC-M11-12 (Sidebar 8 mục + Quản trị per role, 06 §3.2/§3.4) and TC-M11-13
 * (v2.1 routes → 308 to v3). Backend-independent → runs on `mock` and `real`.
 */
const ALL = ["home", "ask", "goals", "work", "meetings", "data", "business", "knowledge", "admin"] as const;
const EXEC = ["home", "ask", "goals", "work", "meetings", "data", "business", "knowledge"];

const SIDEBAR: readonly (readonly [string, readonly string[]])[] = [
  ["ceo@abc.demo", ALL],
  ["cfo@abc.demo", EXEC],
  ["hr@abc.demo", ALL], // DIR khối O → Quản trị (cơ cấu, R-DEC-30; T-617F)
  ["manager@abc.demo", EXEC],
  ["employee@abc.demo", EXEC],
  ["reviewer@abc.demo", ["home", "ask", "data", "business", "knowledge"]],
  ["admin@abc.demo", ["home", "ask", "data", "knowledge", "admin"]],
];

test.describe("IA v3 sidebar per role (TC-M11-12)", { tag: "@mock" }, () => {
  for (const [email, keys] of SIDEBAR) {
    test(`${email}: ${keys.length} items`, async ({ page }) => {
      await login(page, email);
      await expect(page).toHaveURL(/\/home$/);
      const items = page.getByTestId("sidebar").locator("[data-testid^=nav-]");
      await expect(items).toHaveCount(keys.length);
      expect(await items.evaluateAll((els) => els.map((e) => e.getAttribute("data-testid")))).toEqual(keys.map((k) => `nav-${k}`));
      // a hidden item is not reachable by URL either (default deny, 06 §3.3)
      const hidden = ALL.find((k) => !keys.includes(k));
      if (hidden) {
        await page.goto(`/${hidden}`);
        await expect(page.getByTestId("forbidden")).toBeVisible();
      }
    });
  }

  test("a not-yet-built item shows the 'Sắp có' frame", async ({ page }) => {
    await login(page, "employee@abc.demo");
    await page.getByTestId("nav-meetings").click();
    await expect(page).toHaveURL(/\/meetings$/);
    await expect(page.getByTestId("coming-soon")).toHaveAttribute("data-scr", "SCR-44");
    await expect(page.getByTestId("coming-soon")).toContainText("Sắp có");
  });

  test("locale cookie NEXT_LOCALE switches the IA to English", async ({ page, context }) => {
    await login(page, "manager@abc.demo");
    await context.addCookies([{ name: "NEXT_LOCALE", value: "en", url: page.url() }]);
    await page.reload();
    await expect(page.getByTestId("nav-meetings")).toContainText("Meetings & calendar");
  });
});

const REDIRECTS = [
  ["/dashboard", "/home"],
  ["/dashboard/pillar/finance?period=2026-10", "/home/pillar/finance?period=2026-10"],
  ["/ai", "/ask"],
  ["/idp/review", "/data/review"],
  ["/idp/review/0b7c6f7e-2a3d-4f7e-9a51-3d2c1b0a9e88", "/data/review/0b7c6f7e-2a3d-4f7e-9a51-3d2c1b0a9e88"],
  ["/finance/invoices", "/business/finance/invoices"],
  ["/hr/employees", "/business/hr/employees"],
  ["/approvals", "/work/approvals"],
] as const;

test.describe("v2.1 routes redirect 308 (TC-M11-13)", { tag: "@mock" }, () => {
  for (const [from, to] of REDIRECTS) {
    test(`${from} → ${to}`, async ({ request }) => {
      const res = await request.get(from, { maxRedirects: 0 });
      expect(res.status()).toBe(308);
      const loc = new URL(res.headers().location ?? "", "http://placeholder");
      expect(loc.pathname + loc.search).toBe(to);
    });
  }

  test("an old bookmark ends on the v3 page after login", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/\/login\?callbackUrl=%2Fhome/);
  });
});

test.describe("product/risk frozen (TC-M11-14, R-DEC-16)", { tag: "@mock" }, () => {
  test("CEO Executive default has no U/S card; the 5 pillars live only on SCR-03", async ({ page }) => {
    await login(page, "ceo@abc.demo");
    const grid = page.getByTestId("pillar-grid");
    await expect(grid.getByTestId("pillar-F")).toBeVisible();
    await expect(grid.getByTestId("pillar-U")).toHaveCount(0);
    await expect(grid.getByTestId("pillar-S")).toHaveCount(0);
    await expect(page.locator("[data-testid^=nav-product], [data-testid^=nav-risk]")).toHaveCount(0);
    await page.getByTestId("five-pillar-link").click();
    // first client navigation to SCR-03 compiles the route on demand under `next dev` (mock)
    await expect(page).toHaveURL(/\/home\/pillar\/finance/, { timeout: 30_000 });
    await expect(page.getByTestId("pillar-tabs").locator("a")).toHaveCount(5);
  });

  test("a DIR scoped to F gets no five-pillar link", async ({ page }) => {
    await login(page, "cfo@abc.demo");
    await expect(page.getByTestId("pillar-F")).toBeVisible();
    await expect(page.getByTestId("five-pillar-link")).toHaveCount(0);
  });
});

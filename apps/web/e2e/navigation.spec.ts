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
      // SCR-40 (R-DEC-84/85): REV lands on /data, ADM on /admin, còn lại /home — sidebar vẫn đủ mục.
      await expect(page).toHaveURL(/\/(home|data|admin)/);
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

  test("knowledge (SCR-49) is now built — renders the /knowledge view, not the 'Sắp có' frame", async ({ page }) => {
    await login(page, "employee@abc.demo");
    // SCR-49 was a ComingSoon frame until M3.3 (Decision Log + Reports) / M3.4 (Documents).
    await page.getByTestId("nav-knowledge").click();
    await expect(page).toHaveURL(/\/knowledge$/);
    await expect(page.getByTestId("knowledge-view")).toBeVisible();
    await expect(page.getByTestId("knowledge-tabs")).toBeVisible();
    await expect(page.getByTestId("coming-soon")).toHaveCount(0);
  });

  test("meetings (SCR-44) is now built — renders the /meetings view", async ({ page }) => {
    await login(page, "employee@abc.demo");
    await page.getByTestId("nav-meetings").click();
    await expect(page).toHaveURL(/\/meetings$/);
    await expect(page.getByTestId("meetings-view")).toBeVisible();
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

test.describe("product/risk frozen (TC-M11-14, R-DEC-16/82)", { tag: "@mock" }, () => {
  test("CEO: không có nav product/risk; 5 trụ chỉ ở SCR-03 (/home/pillar)", async ({ page }) => {
    await login(page, "ceo@abc.demo");
    await expect(page).toHaveURL(/\/home$/);
    // SCR-40: trang chủ là Reporting v3 (không còn lưới 5 trụ). Product/Risk đóng băng → không có nav.
    await expect(page.getByTestId("exec-view")).toBeVisible();
    await expect(page.locator("[data-testid^=nav-product], [data-testid^=nav-risk]")).toHaveCount(0);
    // layout 5 trụ chỉ sống ở SCR-03
    await page.goto("/home/pillar/finance");
    await expect(page.getByTestId("pillar-tabs").locator("a")).toHaveCount(5);
  });
});

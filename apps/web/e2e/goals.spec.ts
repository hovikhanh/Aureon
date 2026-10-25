import { execFileSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import type { Browser, Page } from "@playwright/test";
import { expect, test } from "./fixtures";
import { login } from "./helpers";
import { rootEnv } from "./support/seed";

/**
 * T-626F..T-628F — M1.4 goals screens on the mock BFF (API_MODE=mock): SCR-41 tree per role
 * (EMP own + restricted ancestors, CEO full + quick filter), SCR-58 KPI detail (band, chart,
 * target versions, "Ghi số đo"), SCR-59 Objective/KR (at-risk reasons, check-in history),
 * SCR-60 F4 check-in (EMP cards → "Đã check-in", MGR team feed). `@mock-only`: the seeded
 * store (seeded from `seed_snapshot.json` = the API seed) is reset per server; the real-stack
 * flow is the `@real-only` block below (T-633, TC-M14-18).
 */
test.describe("M1.4 goals screens", { tag: ["@mock", "@mock-only"] }, () => {
  test("CEO: tree Strategy → SO → KPI/OKR/Initiative, UC-03 CRITICAL, UC-04 at risk, quick filter, unaligned last", async ({ page }) => {
    await login(page, "ceo@abc.demo");
    await page.goto("/goals");
    const tree = page.getByTestId("goals-tree");
    await expect(tree).toHaveAttribute("data-scr", "SCR-41");
    await expect(page.getByTestId("goals-tab-tree")).toHaveAttribute("aria-current", "page");
    for (const so of ["SO-01", "SO-02", "SO-03", "SO-04"]) await expect(page.getByTestId(`so-node-${so}`)).toBeVisible();
    await expect(page.getByTestId("kpi-node-KPI-SAL-01").getByTestId("band-chip").first()).toHaveAttribute("data-band", "CRITICAL");
    await expect(page.locator('[data-testid^="kr-node-"][data-at-risk="true"]')).toHaveCount(1);
    await expect(page.getByTestId("ini-node-INI-03").getByTestId("on-track")).toHaveText("Trễ");
    await expect(page.getByTestId("ini-node-INI-04").getByTestId(/^ini-project-/)).toHaveCount(2);
    await expect(page.getByTestId("goals-unaligned")).toHaveCount(0); // seed: every root is aligned
    await page.getByTestId("goals-flagged").click();
    await expect(page).toHaveURL(/flagged=1/);
    await expect(page.getByTestId("kpi-node-KPI-SVC-01")).toHaveCount(0);
    await expect(page.getByTestId("kpi-node-KPI-SAL-01")).toBeVisible();
  });

  test("EMP: only own KR + restricted ancestors (not clickable), no create buttons", async ({ page }) => {
    await login(page, "employee@abc.demo");
    await page.goto("/goals");
    await expect(page.getByTestId("so-node-SO-04")).toHaveAttribute("data-restricted", "true");
    await expect(page.locator('[data-testid^="obj-restricted-"]')).not.toHaveCount(0);
    await expect(page.locator('a:has([data-restricted="true"]), a[data-restricted="true"]')).toHaveCount(0);
    await expect(page.getByTestId("kpi-node-KPI-SVC-02")).toHaveCount(0); // seed: EMP owns one KR, no KPI
    await expect(page.getByTestId("kpi-node-KPI-SAL-01")).toHaveCount(0);
    await expect(page.getByTestId(/^kr-checkin-/)).toHaveCount(1);
    await expect(page.getByTestId("goals-createKpi")).toHaveCount(0);
    await expect(page.getByTestId("goals-strategy")).toHaveCount(0);
  });

  test("SCR-58: KPI-SAL-01 band + chart + target versions; CEO records a measurement (zod + toast + history)", async ({ page }) => {
    await login(page, "ceo@abc.demo");
    await page.goto("/goals");
    await page.getByTestId("kpi-node-KPI-SAL-01").getByRole("link").first().click();
    const detail = page.getByTestId("kpi-detail");
    await expect(detail).toHaveAttribute("data-scr", "SCR-58");
    await expect(page.getByTestId("kpi-status").getByTestId("band-chip")).toHaveAttribute("data-band", "CRITICAL");
    await expect(page.getByTestId("kpi-chart")).toBeVisible();
    await expect(page.getByTestId("target-open")).toHaveCount(3); // 2026-07..09, no mid-period change in the seed
    await page.getByTestId("kpi-tab-links").click();
    await expect(page.getByTestId("kpi-links")).toContainText("KPI-CO-01");
    await page.getByTestId("kpi-tab-ai").click();
    await expect(page.getByTestId("kpi-ai")).toBeVisible();

    // write on another KPI so the UC-03 state above stays intact for later specs
    await page.goto("/goals");
    await page.getByTestId("kpi-node-KPI-PRD-01").getByRole("link").first().click();
    await expect(page.getByTestId("kpi-detail")).toContainText("KPI-PRD-01");
    await page.getByTestId("kpi-measure").click();
    await page.getByTestId("m-value").fill("abc");
    await page.getByTestId("m-submit").click();
    await expect(page.getByTestId("measure-dialog")).toContainText("Vui lòng nhập một số hợp lệ.");
    await page.getByTestId("m-value").fill("34");
    await page.getByTestId("m-submit").click();
    await expect(page.getByTestId("measure-dialog")).toHaveCount(0);
    await expect(page.getByText("Đã ghi số đo.")).toBeVisible();
    await page.getByTestId("kpi-tab-history").click();
    await expect(page.getByTestId("measurement-row").first()).toContainText("T10/2026");
  });

  test("SCR-59: UC-04 KR at-risk reasons + check-in history with sparkline", async ({ page }) => {
    await login(page, "sales@abc.demo");
    await page.goto("/goals");
    await page.locator('[data-testid^="kr-node-"][data-at-risk="true"]').getByRole("link").first().click();
    await expect(page.getByTestId("objective-detail")).toHaveAttribute("data-scr", "SCR-59");
    await expect(page).toHaveURL(/\?kr=/);
    const risky = page.locator('[data-testid^="kr-item-"][data-at-risk="true"]');
    await expect(risky.getByTestId("at-risk-reasons")).toContainText("Độ tin cậy thấp");
    await expect(risky.getByTestId("kr-last-checkin")).toContainText("check-in gần nhất 4 ngày trước");
    await expect(page.getByTestId("kr-history-row")).toHaveCount(2);
    await expect(page.getByTestId("kr-sparkline")).toBeVisible();
    await expect(page.getByTestId("kr-history-row").first()).toContainText("thiếu presales");
  });

  test("SCR-60: EMP F4 cards (prefill placeholder) → check-in → 'Đã check-in'; MGR sees it in the team feed", async ({ page, browser }) => {
    await login(page, "employee@abc.demo");
    await page.goto("/goals/check-ins");
    await expect(page.getByTestId("checkins")).toHaveAttribute("data-scr", "SCR-60");
    await expect(page.getByTestId("checkins-tab-team")).toHaveCount(0);
    const card = page.locator('[data-testid^="checkin-card-"][data-target-type="key_result"]');
    await expect(card).toHaveAttribute("data-done", "true"); // checked in 16/10, business day 20/10
    await expect(card.getByTestId("checkin-prefill")).toHaveAttribute("data-prefill", "null");
    await card.getByTestId("checkin-value").fill("1,85");
    await card.getByTestId("checkin-conf-HIGH").click();
    await card.getByTestId("checkin-note").fill("Tuyến Thủ Đức ổn định");
    await card.getByTestId("checkin-submit").click();
    await expect(card.getByTestId("checkin-done")).toBeVisible();
    await expect(page.getByText(/^Đã check-in /)).toBeVisible();

    const ctx = await browser.newContext({ locale: "vi-VN", timezoneId: "Asia/Ho_Chi_Minh" });
    const mgr = await ctx.newPage();
    await login(mgr, "manager@abc.demo");
    await mgr.goto("/goals/check-ins");
    await mgr.getByTestId("checkins-tab-team").click();
    await expect(mgr.getByTestId("checkin-feed")).toContainText("Tuyến Thủ Đức ổn định");
    await mgr.getByTestId("cf-confidence").selectOption("LOW");
    await expect(mgr.getByTestId("feed-row")).toHaveCount(0);
    await expect(mgr.getByTestId("checkins-missing")).toBeVisible();
    await ctx.close();
  });

  test("REV / ADM: /goals and sub-routes → 403", async ({ page }) => {
    await login(page, "reviewer@abc.demo");
    for (const p of ["/goals", "/goals/check-ins", "/goals/kpis/x"]) {
      await page.goto(p);
      await expect(page.getByTestId("forbidden")).toBeVisible();
    }
  });
});

/**
 * T-633 / TC-M14-18 — M1.4 exit on the real stack (API + web + Celery worker/beat): the seeded tree
 * (UC-03 KPI-SAL-01 CRITICAL, UC-04 exactly one KR at risk, EMP = own KR under restricted
 * ancestors); EMP checks in on its KR (F4) → MGR sees it in the team feed; DIR Sales checks in
 * lower + LOW on OKR-SAL #0 → KR at risk → `execution.okr_at_risk` → consumer → `alert` in the
 * bell (link SCR-59). `@real-only`: writes to the dev DB — `support/goals_e2e.py` undoes them.
 */
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../..");

function goalsCleanup(): void {
  execFileSync(path.join(ROOT, ".venv/bin/python"), [path.join(ROOT, "apps/web/e2e/support/goals_e2e.py"), "--cleanup"], {
    cwd: ROOT, env: { ...process.env, ...rootEnv(), PYTHONPATH: "apps/api/src:apps/api" }, encoding: "utf8", timeout: 120_000,
  });
}

async function session(browser: Browser, email: string): Promise<Page> {
  const page = await (await browser.newContext()).newPage();
  await login(page, email);
  return page;
}

test.describe("M1.4 goals on the real stack (TC-M14-18)", { tag: "@real-only" }, () => {
  test.describe.configure({ mode: "serial" });
  test.beforeAll(() => goalsCleanup());
  test.afterAll(() => goalsCleanup());

  test("seeded tree: CEO UC-03 CRITICAL + exactly 1 KR at risk; EMP own KR under restricted SO-04", async ({ browser }) => {
    const ceo = await session(browser, "ceo@abc.demo");
    await ceo.goto("/goals");
    for (const so of ["SO-01", "SO-02", "SO-03", "SO-04"]) await expect(ceo.getByTestId(`so-node-${so}`)).toBeVisible();
    await expect(ceo.getByTestId("kpi-node-KPI-SAL-01").getByTestId("band-chip").first()).toHaveAttribute("data-band", "CRITICAL");
    await expect(ceo.locator('[data-testid^="kr-node-"][data-at-risk="true"]')).toHaveCount(1);
    await expect(ceo.locator('[data-testid^="kr-node-"][data-at-risk="true"]')).toContainText("Pipeline trọng số");
    await expect(ceo.getByTestId("ini-node-INI-03").getByTestId("on-track")).toHaveText("Trễ");
    await expect(ceo.getByTestId("ini-node-INI-04").getByTestId(/^ini-project-/)).toHaveCount(2);

    const emp = await session(browser, "employee@abc.demo");
    await emp.goto("/goals");
    await expect(emp.getByTestId("so-node-SO-04")).toHaveAttribute("data-restricted", "true");
    await expect(emp.locator('[data-testid^="obj-restricted-"]')).toHaveCount(1);
    await expect(emp.getByTestId(/^kr-checkin-/)).toHaveCount(1);
    await expect(emp.locator('[data-testid^="kr-node-"]')).toContainText("Giao hàng TB ≤ 1,8 ngày");
    await expect(emp.getByTestId("kpi-node-KPI-SAL-01")).toHaveCount(0);
    await expect(emp.getByTestId("goals-createKpi")).toHaveCount(0);
  });

  test("EMP checks in on own KR (F4) → MGR sees it in the team feed", async ({ browser }) => {
    const note = `E2E goals ${Date.now().toString(36)}`;
    const emp = await session(browser, "employee@abc.demo");
    await emp.goto("/goals/check-ins");
    const card = emp.locator('[data-testid^="checkin-card-"][data-target-type="key_result"]');
    await expect(card).toHaveCount(1);
    await card.getByTestId("checkin-value").fill("1,85");
    await card.getByTestId("checkin-conf-HIGH").click();
    await card.getByTestId("checkin-note").fill(note);
    await card.getByTestId("checkin-submit").click();
    await expect(card.getByTestId("checkin-done")).toBeVisible();
    await expect(emp.getByText(/^Đã check-in /)).toBeVisible();

    const mgr = await session(browser, "manager@abc.demo");
    await mgr.goto("/goals/check-ins");
    await mgr.getByTestId("checkins-tab-team").click();
    await expect(mgr.getByTestId("checkin-feed").getByTestId("feed-row").filter({ hasText: note })).toContainText("Giao hàng TB ≤ 1,8 ngày");
  });

  test("DIR check-in drops OKR-SAL #0 → KR at risk → `alert` in the bell (Celery consumer) → SCR-59", async ({ browser }) => {
    test.setTimeout(180_000);
    const sales = await session(browser, "sales@abc.demo");
    await sales.goto("/goals/check-ins");
    const card = sales.locator('[data-testid^="checkin-card-"]').filter({ hasText: "Ký 6 hợp đồng khách hàng lớn" });
    await card.getByTestId("checkin-value").fill("1");
    await card.getByTestId("checkin-conf-LOW").click();
    await card.getByTestId("checkin-note").fill(`E2E goals ${Date.now().toString(36)} mất 1 hợp đồng`);
    await card.getByTestId("checkin-submit").click();
    await expect(sales.getByText(/^Đã check-in /)).toBeVisible();

    // outbox relay (beat) → execution.on_goal_alert (worker) → notification for the KR owner
    const item = sales.getByTestId("notification-item").filter({ hasText: "KR có rủi ro kỳ 2026-Q4" });
    await expect(async () => {
      await sales.reload();
      await sales.getByTestId("notification-bell").click();
      await expect(item.first()).toBeVisible({ timeout: 3_000 });
    }).toPass({ timeout: 120_000, intervals: [2_000, 5_000] });
    await item.first().click();
    await expect(sales).toHaveURL(/\/goals\/objectives\/[0-9a-f-]+\?kr=/);
    await expect(sales.getByTestId("objective-detail")).toHaveAttribute("data-scr", "SCR-59");
    const risky = sales.locator('[data-testid^="kr-item-"][data-at-risk="true"]');
    await expect(risky).toHaveCount(2);
    await expect(risky.filter({ hasText: "Ký 6 hợp đồng" }).getByTestId("at-risk-reasons")).toContainText("Độ tin cậy thấp");
  });
});

import { expect, test } from "@playwright/test";
import { login } from "./helpers";

/**
 * T-626F..T-628F — M1.4 goals screens on the mock BFF (API_MODE=mock): SCR-41 tree per role
 * (EMP own + restricted ancestors, CEO full + quick filter), SCR-58 KPI detail (band, chart,
 * target versions, "Ghi số đo"), SCR-59 Objective/KR (at-risk reasons, check-in history),
 * SCR-60 F4 check-in (EMP cards → "Đã check-in", MGR team feed). `@mock-only`: the seeded
 * store (UC-03 / UC-04, EMP-owned KR + KPI) is mock-only until T-631; the real-stack flow is
 * T-626..T-628 (TC-M14 integration).
 */
test.describe("M1.4 goals screens", { tag: ["@mock", "@mock-only"] }, () => {
  test("CEO: tree Strategy → SO → KPI/OKR/Initiative, UC-03 CRITICAL, UC-04 at risk, quick filter, unaligned last", async ({ page }) => {
    await login(page, "ceo@abc.demo");
    await page.goto("/goals");
    const tree = page.getByTestId("goals-tree");
    await expect(tree).toHaveAttribute("data-scr", "SCR-41");
    await expect(page.getByTestId("goals-tab-tree")).toHaveAttribute("aria-current", "page");
    for (const so of ["SO-C", "SO-F", "SO-U", "SO-O"]) await expect(page.getByTestId(`so-node-${so}`)).toBeVisible();
    await expect(page.getByTestId("kpi-node-KPI-SAL-01").getByTestId("band-chip").first()).toHaveAttribute("data-band", "CRITICAL");
    await expect(page.locator('[data-testid^="kr-node-"][data-at-risk="true"]')).toHaveCount(1);
    await expect(page.getByTestId("ini-node-INI-03").getByTestId("on-track")).toHaveText("Trễ");
    await expect(page.getByTestId("ini-node-INI-04").getByTestId(/^ini-project-/)).toHaveCount(2);
    await expect(page.getByTestId("goals-unaligned")).toContainText("KPI-ADM-01");
    await page.getByTestId("goals-flagged").click();
    await expect(page).toHaveURL(/flagged=1/);
    await expect(page.getByTestId("kpi-node-KPI-SVC-01")).toHaveCount(0);
    await expect(page.getByTestId("kpi-node-KPI-SAL-01")).toBeVisible();
  });

  test("EMP: only own KR/KPI + restricted ancestors (not clickable), no create buttons", async ({ page }) => {
    await login(page, "employee@abc.demo");
    await page.goto("/goals");
    await expect(page.getByTestId("so-node-SO-O")).toHaveAttribute("data-restricted", "true");
    await expect(page.locator('[data-testid^="obj-restricted-"]')).not.toHaveCount(0);
    await expect(page.locator('a:has([data-restricted="true"]), a[data-restricted="true"]')).toHaveCount(0);
    await expect(page.getByTestId("kpi-node-KPI-SVC-02")).toBeVisible();
    await expect(page.getByTestId("kpi-node-KPI-SAL-01")).toHaveCount(0);
    await expect(page.getByTestId(/^kr-checkin-/)).toHaveCount(1);
    await expect(page.getByTestId("goals-createKpi")).toHaveCount(0);
    await expect(page.getByTestId("goals-strategy")).toHaveCount(0);
  });

  test("SCR-58: KPI-SAL-01 band + chart + closed target version; CEO records a measurement (zod + toast + history)", async ({ page }) => {
    await login(page, "ceo@abc.demo");
    await page.goto("/goals");
    await page.getByTestId("kpi-node-KPI-SAL-01").getByRole("link").first().click();
    const detail = page.getByTestId("kpi-detail");
    await expect(detail).toHaveAttribute("data-scr", "SCR-58");
    await expect(page.getByTestId("kpi-status").getByTestId("band-chip")).toHaveAttribute("data-band", "CRITICAL");
    await expect(page.getByTestId("kpi-chart")).toBeVisible();
    await expect(page.getByTestId("target-change")).toContainText("đổi ngày 15/09/2026 — Điều chỉnh theo thị trường Q3");
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
    await expect(page.getByTestId("kr-history-row").first()).toContainText("Thiếu presales");
  });

  test("SCR-60: EMP F4 cards (prefill placeholder) → check-in → 'Đã check-in'; MGR sees it in the team feed", async ({ page, browser }) => {
    await login(page, "employee@abc.demo");
    await page.goto("/goals/check-ins");
    await expect(page.getByTestId("checkins")).toHaveAttribute("data-scr", "SCR-60");
    await expect(page.getByTestId("checkins-tab-team")).toHaveCount(0);
    const card = page.locator('[data-testid^="checkin-card-"][data-target-type="key_result"]');
    await expect(card).toHaveAttribute("data-done", "false");
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

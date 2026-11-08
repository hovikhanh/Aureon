import type { Locator, Page } from "@playwright/test";
import { expect, test } from "./fixtures";
import { loginSettled } from "./helpers";

/**
 * TC-M5-08 (e2e) — KPI / OKR create · view · edit · archive end-to-end (M5 issue 2).
 * "Tạo KPI" / "Tạo Objective" on /goals were disabled "coming soon" buttons although the API
 * (EP-KPI-02/04/05, EP-OKR-02/04/05/07/09/10) was complete.
 */
/**
 * Sign in, let the post-login redirect (`/` → `/home`) finish, then open /goals and wait for the
 * tree. Navigating while the redirect is still in flight overlapped two navigations and, under
 * parallel load, left a stale copy of the tree in the DOM for a moment (strict-mode violations).
 */
async function openGoals(page: Page, email: string): Promise<void> {
  await loginSettled(page, email);
  await page.goto("/goals");
  await expect(page.getByTestId("goals-tree")).toBeVisible();
}

/** Select the first non-default option (needs ≥ 2 options: the default plus a loaded one) → its value. */
async function pickSecond(select: Locator): Promise<string> {
  await expect(select.locator("option")).not.toHaveCount(1);
  const value = await select.locator("option").nth(1).getAttribute("value");
  await select.selectOption(value!);
  return value!;
}

const uniq = () => `${Date.now().toString(36)}${Math.floor(Math.random() * 1e4)}`.toUpperCase();

test.describe("M5 · goals editors", { tag: "@mock" }, () => {
  test("CEO creates, edits and archives a KPI", async ({ page }) => {
    const code = `KPI-E2E-${uniq()}`;
    await openGoals(page, "ceo@abc.demo");
    await page.getByTestId("goals-createKpi").click();
    const dlg = page.getByTestId("kpi-editor");
    await dlg.getByTestId("ke-code").fill(code);
    await dlg.getByTestId("ke-unit").fill("%");
    await dlg.getByTestId("ke-name").fill("Tỷ lệ giao hàng đúng hẹn E2E");
    await dlg.getByTestId("ke-target").fill("95,5");
    await dlg.getByTestId("ke-period-type").selectOption("MONTH");
    await dlg.getByTestId("ke-value-type").selectOption("percentage");
    // CEO picks the department from `/hr/departments` (existing API) and another owner (`/platform/users`)
    const dept = await pickSecond(dlg.getByTestId("ke-department"));
    const owner = await pickSecond(dlg.getByTestId("ke-owner"));
    const created = page.waitForResponse((r) => r.request().method() === "POST" && /\/api\/backend\/kpis$/.test(r.url()));
    await dlg.getByTestId("kpi-editor-submit").click();
    const kpi = (await (await created).json()).data;
    expect([kpi.department_id, kpi.owner_id]).toEqual([dept, owner]);

    await expect(page).toHaveURL(/\/goals\/kpis\/[0-9a-f-]+$/);
    await expect(page.getByTestId("kpi-detail")).toContainText(code);

    await page.getByTestId("kpi-edit").click();
    await expect(page.getByTestId("ke-code")).toBeDisabled(); // the code is the KPI's stable key
    await expect(page.getByTestId("ke-department")).toHaveValue(dept);
    await page.getByTestId("ke-name").fill("Tỷ lệ giao hàng đúng hẹn (sửa)");
    await page.getByTestId("ke-department").selectOption(""); // → company level
    const patched = page.waitForResponse((r) => r.request().method() === "PATCH" && /\/api\/backend\/kpis\//.test(r.url()));
    await page.getByTestId("kpi-editor-submit").click();
    expect((await (await patched).json()).data.department_id).toBeNull();
    await expect(page.getByTestId("kpi-editor")).toHaveCount(0);
    await expect(page.getByRole("heading", { level: 1 })).toContainText("(sửa)");

    await page.getByTestId("kpi-archive").click();
    await page.getByTestId("archive-confirm").click();
    await expect(page).toHaveURL(/\/goals$/);
  });

  test("a duplicate KPI code is refused in place (409 DUPLICATE_RESOURCE), dialog stays open", async ({ page }) => {
    const code = `KPI-DUP-${uniq()}`;
    await openGoals(page, "ceo@abc.demo");
    for (const attempt of [1, 2]) {
      if (attempt === 2) await page.goto("/goals");
      await expect(page.getByTestId("goals-tree")).toBeVisible();
      await page.getByTestId("goals-createKpi").click();
      const dlg = page.getByTestId("kpi-editor");
      await dlg.getByTestId("ke-code").fill(code);
      await dlg.getByTestId("ke-unit").fill("lần");
      await dlg.getByTestId("ke-name").fill(`Trùng mã ${attempt}`);
      await dlg.getByTestId("ke-target").fill("10");
      await dlg.getByTestId("kpi-editor-submit").click();
      if (attempt === 1) await expect(page).toHaveURL(/\/goals\/kpis\//);
      else await expect(dlg.getByTestId("kpi-editor-error")).toBeVisible();
    }
  });

  test("CEO creates an Objective, adds / edits / archives a key result, then archives the Objective", async ({ page }) => {
    const title = `Mở rộng kênh đại lý E2E ${uniq()}`;
    await openGoals(page, "ceo@abc.demo");
    await page.getByTestId("goals-createObjective").click();
    const dlg = page.getByTestId("objective-editor");
    await dlg.getByTestId("oe-title").fill(title);
    await expect(dlg.getByTestId("oe-period")).not.toHaveValue("");
    await dlg.getByTestId("oe-level").selectOption("department");
    const dept = await pickSecond(dlg.getByTestId("oe-department"));
    const created = page.waitForResponse((r) => r.request().method() === "POST" && /\/api\/backend\/objectives$/.test(r.url()));
    await dlg.getByTestId("objective-editor-submit").click();
    expect((await (await created).json()).data.department_id).toBe(dept);

    await expect(page).toHaveURL(/\/goals\/objectives\/[0-9a-f-]+$/);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(title);

    await page.getByTestId("kr-add").click();
    const kr = page.getByTestId("kr-editor");
    await kr.getByTestId("re-title").fill("Ký 12 đại lý mới");
    await kr.getByTestId("re-baseline").fill("0");
    await kr.getByTestId("re-target").fill("12");
    await kr.getByTestId("re-unit").fill("đại lý");
    await kr.getByTestId("kr-editor-submit").click();
    const item = page.getByTestId("objective-krs").locator("li").filter({ hasText: "Ký 12 đại lý mới" });
    await expect(item).toBeVisible();

    await item.getByRole("button", { name: /sửa|edit/i }).click();
    await page.getByTestId("re-target").fill("15");
    await page.getByTestId("kr-editor-submit").click();
    await expect(item).toContainText("15");

    await item.getByRole("button", { name: /lưu trữ|archive/i }).click();
    await page.getByTestId("archive-confirm").click();
    await expect(page.getByTestId("objective-krs").locator("li").filter({ hasText: "Ký 12 đại lý mới" })).toHaveCount(0);

    await page.getByTestId("objective-archive").click();
    await page.getByTestId("archive-confirm").click();
    await expect(page).toHaveURL(/\/goals$/);
  });

  test("an employee sees no create / edit / archive controls (API enforces too)", async ({ page }) => {
    await openGoals(page, "employee@abc.demo");
    await expect(page.getByTestId("goals-tree")).toBeVisible();
    await expect(page.getByTestId("goals-createKpi")).toHaveCount(0);
    await expect(page.getByTestId("goals-createObjective")).toHaveCount(0);
  });
});

test.describe("F12 strategies", { tag: "@mock" }, () => {
  test("CEO creates a strategy, then a strategic objective under it", async ({ page }) => {
    await openGoals(page, "ceo@abc.demo");
    await page.getByTestId("goals-strategies").click();
    await expect(page).toHaveURL(/\/goals\/strategies$/);
    const code = `ST-${uniq()}`;
    await page.getByTestId("strategy-create").click();
    await page.getByTestId("st-code").fill(code);
    await page.getByTestId("st-name").fill("Chiến lược thử nghiệm");
    await page.getByTestId("st-start").fill("2030-01-01");
    await page.getByTestId("st-end").fill("2030-12-31");
    await page.getByTestId("strategy-editor-submit").click();
    const row = page.locator(`[data-testid=strategy-row][data-code="${code}"]`);
    await expect(row).toBeVisible();
    await row.click();
    await expect(page.getByTestId("so-empty")).toBeVisible();
    await page.getByTestId("so-create").click();
    await page.getByTestId("so-code").fill(`SO-${uniq()}`);
    await page.getByTestId("so-title").fill("Mục tiêu thử nghiệm");
    await page.getByTestId("so-editor-submit").click();
    await expect(page.getByTestId("so-row")).toContainText("Mục tiêu thử nghiệm");
  });

  test("a date range the API refuses is stopped in the form", async ({ page }) => {
    await openGoals(page, "ceo@abc.demo");
    await page.goto("/goals/strategies");
    await page.getByTestId("strategy-create").click();
    await page.getByTestId("st-code").fill("ST-X");
    await page.getByTestId("st-name").fill("X");
    await page.getByTestId("st-start").fill("2030-12-31");
    await page.getByTestId("st-end").fill("2030-01-01");
    await page.getByTestId("strategy-editor-submit").click();
    await expect(page.getByTestId("strategy-editor")).toContainText("Ngày kết thúc phải sau ngày bắt đầu");
  });

  test("EMP has no way in; MGR reads without create", async ({ page, browser }) => {
    await loginSettled(page, "employee@abc.demo");
    await page.goto("/goals/strategies");
    await expect(page.getByTestId("forbidden")).toBeVisible();
    const context = await browser.newContext({ baseURL: test.info().project.use.baseURL, locale: "vi-VN" });
    const mgr = await context.newPage();
    await loginSettled(mgr, "manager@abc.demo");
    await mgr.goto("/goals/strategies");
    await expect(mgr.getByTestId("strategy-list")).toBeVisible();
    await expect(mgr.getByTestId("strategy-create")).toHaveCount(0);
    await expect(mgr.getByTestId("so-create")).toHaveCount(0);
    await context.close();
  });
});

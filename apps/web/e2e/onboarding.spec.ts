import { expect, test, type Page } from "./fixtures";
import { login } from "./helpers";

/**
 * M1.6 SCR-66 wizard on mock (T-648F, TC-M16-15): ADM runs UC-07 — company → UC-07 sample import (salary column
 * dropped for ADM) → REV approves → ADM commits → users (a failing row does not block the others) →
 * KPI/OKR step "done by CEO/Director" + skip → finish; reload resumes at the open step; `missing_steps`
 * sends the CEO back. `@mock-only`: relies on the mock store seed + UC-07 roster content by file name.
 */
const XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
const logout = (page: Page) => page.context().clearCookies();

test.describe("M1.6 onboarding wizard (TC-M16-15)", { tag: ["@mock", "@mock-only"] }, () => {
  test("ADM: 6 steps end-to-end, resume after reload", async ({ page }) => {
    test.setTimeout(300_000);
    await login(page, "admin@abc.demo");
    await page.goto("/admin");
    await expect(page.getByTestId("onboarding-pending")).toBeVisible();
    await page.getByTestId("admin-card-onboarding").click();
    await page.getByTestId("onboarding-start").click();
    const wizard = page.getByTestId("onboarding");
    await expect(wizard).toHaveAttribute("data-step", "company");
    await expect(page.getByTestId("onboarding-clock")).toHaveAttribute("data-tone", "ok");
    await expect(page.getByTestId("stepper-company")).toHaveAttribute("aria-current", "step");

    await page.getByTestId("company-tax").fill("123");
    await page.getByTestId("company-save").click();
    await expect(page.getByTestId("company-form")).toContainText(/10 số|10 digits/);
    await page.getByTestId("company-tax").fill("0312345678");
    await page.getByTestId("company-save").click();
    await expect(wizard).toHaveAttribute("data-step", "org_import");
    await page.reload();
    await expect(wizard).toHaveAttribute("data-step", "org_import");

    await expect(page.getByTestId("template-link")).toHaveAttribute("href", /ABC_DanhSachNhanSu_Onboarding\.xlsx$/);
    await page.getByTestId("onboarding-file").setInputFiles({ name: "ABC_DanhSachNhanSu_Onboarding.xlsx", mimeType: XLSX, buffer: Buffer.from(`PK mock ${Date.now()}`) });
    await expect(page.getByTestId("sensitive-dropped")).toContainText("Lương", { timeout: 60_000 }); // upload + preview + schema compile on demand
    await page.getByTestId("onboarding-save-mapping").click();
    await expect(page.getByTestId("summary-valid")).toContainText("24"); // = scripts/gen_demo_docs.py uc07_expectations()
    await expect(page.getByTestId("summary-invalid")).toContainText("3");
    const submitted = page.waitForResponse((r) => r.request().method() === "POST" && /\/imports\/[^/]+\/submit$/.test(r.url()));
    await page.getByTestId("onboarding-submit-import").click();
    const docId = ((await (await submitted).json()) as { data: { document: { id: string } } }).data.document.id;
    await expect(wizard).toHaveAttribute("data-step", "review");
    await expect(page.getByTestId("review-waiting")).toBeVisible();
    await expect(page.getByTestId("planned-dept").first()).toBeVisible();

    await logout(page);
    await login(page, "reviewer@abc.demo");
    const ap = await page.request.post(`/api/backend/idp/documents/${docId}/review/approve`, { headers: { "Idempotency-Key": `e2e-ob-${Date.now()}` }, data: {} });
    expect(ap.status()).toBe(200);
    await logout(page);
    await login(page, "admin@abc.demo");
    await page.goto("/admin/onboarding");
    await expect(wizard).toHaveAttribute("data-step", "review");
    await page.getByTestId("review-commit").click();
    await expect(page.getByTestId("real-tree")).toBeVisible();
    await expect(page.getByTestId("review-undo")).toBeVisible();
    await page.getByTestId("review-confirm").click();

    await expect(wizard).toHaveAttribute("data-step", "users");
    await expect(page.locator('[data-testid="user-role"] option[value="CEO"]')).toHaveCount(0);
    const rows = page.getByTestId("user-row");
    await rows.nth(0).getByTestId("user-email").fill("not-an-email");
    await rows.nth(0).getByTestId("user-generate").click();
    await rows.nth(1).getByTestId("user-email").fill(`ob-${Date.now()}@abc.demo`);
    await rows.nth(1).getByTestId("user-generate").click();
    await page.getByTestId("users-create").click();
    await expect(rows.nth(0)).toHaveAttribute("data-result", "error");
    await expect(rows.nth(1)).toHaveAttribute("data-result", "ok");
    await page.getByTestId("users-enough").click();

    await expect(wizard).toHaveAttribute("data-step", "goals_import");
    await expect(page.getByTestId("goals-not-allowed")).toContainText("CEO/Director");
    await page.getByTestId("goals-skip").click();
    await expect(wizard).toHaveAttribute("data-step", "finish");
    await expect(page.getByTestId("stepper-goals_import")).toHaveAttribute("data-status", "skipped");
    await page.getByTestId("onboarding-finish").click();
    await expect(page.getByTestId("finish-completed")).toBeVisible();
    await expect(wizard).toHaveAttribute("data-status", "completed");
  });

  test("CEO: finish with missing steps → back to the first missing step", async ({ page }) => {
    await login(page, "ceo@abc.demo");
    await page.goto("/admin/onboarding");
    await page.getByTestId("onboarding-start").click();
    await page.getByTestId("stepper-finish").click();
    await page.getByTestId("onboarding-finish").click();
    await expect(page.getByTestId("onboarding")).toHaveAttribute("data-step", "company");
  });
});

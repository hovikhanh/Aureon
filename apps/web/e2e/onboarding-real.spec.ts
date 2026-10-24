import { execFileSync } from "node:child_process";
import { randomUUID } from "node:crypto";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test, type Page } from "./fixtures";
import { login, loginWithPassword } from "./helpers";
import { rootEnv } from "./support/seed";

/**
 * T-650 / TC-M16-23 — UC-07 onboarding on the real stack (API + web + Celery, fixture model gateway):
 * ADM `reset` → org `ABC-E2E` → SCR-66 imports the sample roster (R-DEC-79) → error rows downloadable,
 * valid rows reviewed (REV) + committed → EP-ORG-24 tree = the figures `scripts/gen_demo_docs.py`
 * computes → 3 users (DIR/MGR/EMP) log in → CEO imports DOC-07 → `finish` (`within_one_day`) →
 * `/home`. Then SCR-64 kill switch L0 → banner + refused card in the new EMP's /ask; off → L2
 * ActionCard confirm → task → undo. `support/onboarding_e2e.py --cleanup` before and after.
 *
 * Known limit (reported): ACT-create_department has no organization column (10 §7.2.5), so the rows
 * land in the tenant's first organization (ABC), not in `ABC-E2E`.
 */
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../..");
const XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
const DOC07 = "DOC-07-kpi-okr-q4-2026.xlsx";
const ENV = { ...rootEnv(), ...process.env, PYTHONPATH: "apps/api/src:apps/api" }; // the per-stack overrides of the shell win

interface Expect { file: string; rows_total: number; rows_valid: number; rows_invalid: number; departments: number; employees: number; departments_list: { code: string; headcount: number }[] }

function support(...args: string[]): string {
  return execFileSync(path.join(ROOT, ".venv/bin/python"), [path.join(ROOT, "apps/web/e2e/support/onboarding_e2e.py"), ...args], { cwd: ROOT, env: ENV, encoding: "utf8", timeout: 180_000 });
}
const lastJson = <T,>(out: string): T => JSON.parse(out.trim().split("\n").pop() ?? "{}") as T;
const logout = (page: Page) => page.context().clearCookies();
const idem = () => ({ "Idempotency-Key": randomUUID() });

async function upload(page: Page, name: string): Promise<void> {
  await page.getByTestId("onboarding-file").setInputFiles({ name, mimeType: XLSX, buffer: readFileSync(path.join(ROOT, "data", name)) });
  await expect(page.getByTestId("onboarding-batch")).toBeVisible({ timeout: 60_000 });
  await page.getByTestId("onboarding-save-mapping").click();
  await expect(page.getByTestId("import-summary")).toBeVisible();
}

async function submitImport(page: Page): Promise<string> {
  const submitted = page.waitForResponse((r) => r.request().method() === "POST" && /\/imports\/[^/]+\/submit$/.test(r.url()));
  await page.getByTestId("onboarding-submit-import").click();
  const res = await submitted;
  expect(res.status()).toBe(200);
  return ((await res.json()) as { data: { document: { id: string } } }).data.document.id;
}

async function setKillSwitch(page: Page, on: boolean): Promise<void> {
  await page.goto("/admin/ai");
  await page.getByTestId(on ? "kill-on" : "kill-off").click();
  if (on) await page.getByTestId("kill-mode-select").selectOption("L0");
  await page.getByTestId("kill-reason-input").fill(on ? "E2E sự cố dữ liệu" : "E2E đã xử lý");
  await page.getByTestId("kill-submit").click();
  await expect(page.getByTestId("kill-dialog")).toHaveCount(0);
}

async function ask(page: Page, text: string): Promise<void> {
  await page.goto("/ask");
  await page.getByTestId("chat-input").fill(text);
  await page.getByTestId("chat-send").click();
  await expect(page.getByTestId("assistant-message").last().getByTestId("answer")).not.toBeEmpty({ timeout: 30_000 });
}

test.describe("M1.6 UC-07 onboarding on the real stack (TC-M16-23)", { tag: "@real-only" }, () => {
  test.describe.configure({ mode: "serial" });
  test.beforeAll(() => { support("--cleanup"); });
  test.afterAll(() => { support("--cleanup"); });

  test("ADM reset → import → review → users → CEO goals → finish → kill switch → ActionCard", async ({ page }) => {
    test.setTimeout(600_000);
    const exp = lastJson<Expect>(support("--expect"));
    const run = Date.now();
    const pwd = `E2e-${run.toString(36)}-Ob!x`; // per-run throwaway password of the E2E accounts (≥ 12)
    const users = { DIR: ["OB0001", `dir-${run}@abc-e2e.demo`], MGR: ["OB0003", `mgr-${run}@abc-e2e.demo`], EMP: ["OB0004", `emp-${run}@abc-e2e.demo`] } as const;
    const wizard = page.getByTestId("onboarding");

    await test.step("ADM: reset (demo) + organization ABC-E2E", async () => {
      await login(page, "admin@abc.demo");
      const cur = (await (await page.request.get("/api/backend/platform/onboarding")).json()) as { data: { version: number } };
      const reset = await page.request.patch("/api/backend/platform/onboarding", { headers: idem(), data: { action: "reset", reason: "E2E UC-07", version: cur.data.version } });
      expect(reset.status(), await reset.text()).toBe(200);
      const org = await page.request.post("/api/backend/org/organizations", { headers: idem(), data: { code: "ABC-E2E", name: "ABC E2E" } });
      expect(org.status(), await org.text()).toBe(201);
      await page.goto("/admin/onboarding");
      await page.getByTestId("onboarding-start").click();
      await expect(wizard).toHaveAttribute("data-step", "company");
      await expect(page.getByTestId("company-code")).toHaveValue("ABC-E2E");
      await page.getByTestId("company-tax").fill("0312345678");
      await page.getByTestId("company-save").click();
      await expect(wizard).toHaveAttribute("data-step", "org_import");
    });

    let docId = "";
    await test.step("ADM: sample roster → error rows downloadable → submit valid rows", async () => {
      await expect(page.getByTestId("template-link")).toHaveAttribute("href", new RegExp(`${exp.file.replace(".", "\\.")}$`));
      await upload(page, exp.file);
      await expect(page.getByTestId("summary-valid")).toContainText(String(exp.rows_valid));
      await expect(page.getByTestId("summary-invalid")).toContainText(String(exp.rows_invalid));
      const dl = page.waitForEvent("download");
      await page.getByTestId("import-download-errors").click();
      expect((await dl).suggestedFilename()).toMatch(/\.xlsx$/);
      docId = await submitImport(page);
      await expect(wizard).toHaveAttribute("data-step", "review");
      await expect(page.getByTestId("review-waiting")).toBeVisible();
      await expect(page.getByTestId("planned-dept")).toHaveCount(exp.departments);
    });

    await test.step("REV approves → ADM commits → EP-ORG-24 tree = generator figures", async () => {
      await logout(page);
      await login(page, "reviewer@abc.demo");
      await page.goto(`/data/review/${docId}`);
      await expect(page.getByTestId("grid-row").first()).toBeVisible({ timeout: 30_000 });
      await page.getByTestId("approve").click();
      await expect(page).toHaveURL(/\/data\/review$/);
      await logout(page);
      await login(page, "admin@abc.demo");
      await page.goto("/admin/onboarding");
      await expect(wizard).toHaveAttribute("data-step", "review");
      await page.getByTestId("review-commit").click();
      await expect(page.getByTestId("real-tree")).toBeVisible({ timeout: 60_000 });
      for (const d of exp.departments_list) {
        await expect(page.getByTestId("real-dept").filter({ hasText: `${d.code} — ` })).toContainText(`${d.headcount} người`);
      }
      const tree = (await (await page.request.get("/api/backend/org/tree")).json()) as { data: { departments: { code: string; headcount: number }[] } };
      const ob = tree.data.departments.filter((d) => d.code.startsWith("OB-"));
      expect([ob.length, ob.reduce((n, d) => n + d.headcount, 0)]).toEqual([exp.departments, exp.employees]);
      await page.getByTestId("review-confirm").click();
      await expect(wizard).toHaveAttribute("data-step", "users");
    });

    await test.step("ADM: 3 users DIR / MGR / EMP from the imported people", async () => {
      for (const [role, [code, email]] of Object.entries(users)) {
        const row = page.locator(`[data-testid="user-row"][data-code="${code}"]`);
        await row.getByTestId("user-email").fill(email);
        await row.getByTestId("user-password").fill(pwd);
        await row.getByTestId("user-role").selectOption(role);
      }
      await page.getByTestId("users-create").click();
      for (const [code] of Object.values(users)) await expect(page.locator(`[data-testid="user-row"][data-code="${code}"]`)).toHaveAttribute("data-result", "ok");
      await page.getByTestId("users-enough").click();
      await expect(wizard).toHaveAttribute("data-step", "goals_import");
      await expect(page.getByTestId("goals-not-allowed")).toBeVisible(); // ADM: done by CEO/Director
      for (const [, email] of Object.values(users)) {
        await logout(page);
        await loginWithPassword(page, email, pwd);
        await expect(page).not.toHaveURL(/\/login/);
      }
      // model-gateway fixtures of the new EMP's /ask turn, recorded while the kill switch is off
      expect(lastJson<{ card: string }>(support("--chat", users.EMP[1])).card).toBe("L2");
    });

    await test.step("CEO: DOC-07 KPI/OKR → finish → within one day → /home", async () => {
      await logout(page);
      await login(page, "ceo@abc.demo");
      await page.goto("/admin/onboarding");
      await expect(wizard).toHaveAttribute("data-step", "goals_import");
      await upload(page, DOC07);
      await submitImport(page);
      await expect(wizard).toHaveAttribute("data-step", "finish");
      await page.getByTestId("onboarding-finish").click();
      await expect(page.getByTestId("finish-completed")).toBeVisible();
      await expect(wizard).toHaveAttribute("data-status", "completed");
      const ev = lastJson<{ within_one_day: boolean; duration_minutes: number; counts: Record<string, number> }>(support("--report"));
      expect(ev.within_one_day).toBe(true);
      test.info().annotations.push({ type: "onboarding build time", description: `${ev.duration_minutes} min · ${JSON.stringify(ev.counts)}` });
      console.log(`UC-07 onboarding build time: ${ev.duration_minutes} min`, ev.counts);
      await page.getByTestId("finish-completed").getByRole("link", { name: /dashboard đầu tiên|first dashboard/i }).click();
      await expect(page).toHaveURL(/\/home$/);
      await expect(page.getByTestId("pillar-grid")).toBeVisible({ timeout: 30_000 });
    });

    const ASK = "Tạo việc cho tôi: gọi lại khách hàng ABC trước cuối tháng";
    await test.step("SCR-64 kill switch L0 → banner for the new EMP, /ask card refused", async () => {
      await logout(page);
      await login(page, "admin@abc.demo");
      await setKillSwitch(page, true);
      await expect(page.getByTestId("kill-switch-banner")).toHaveAttribute("data-mode", "L0");
      await logout(page);
      await loginWithPassword(page, users.EMP[1], pwd);
      await expect(page.getByTestId("kill-switch-text")).toHaveText("AI chỉ trả lời, không soạn thao tác");
      await ask(page, ASK);
      await expect(page.getByTestId("chat-warning")).toContainText("Kill switch đang bật");
      await expect(page.getByTestId("action-card")).toHaveCount(0);
    });

    await test.step("kill switch off → L2 ActionCard: confirm → task → undo", async () => {
      await logout(page);
      await login(page, "admin@abc.demo");
      await setKillSwitch(page, false);
      await logout(page);
      await loginWithPassword(page, users.EMP[1], pwd);
      await expect(page.getByTestId("kill-switch-banner")).toHaveCount(0);
      await ask(page, ASK);
      const card = page.getByTestId("action-card");
      await expect(page.getByTestId("action-level")).toHaveText("AI soạn");
      const confirmed = page.waitForResponse((r) => r.request().method() === "POST" && /\/ai\/actions\/[^/]+\/confirm$/.test(r.url()));
      await page.getByTestId("action-confirm").click();
      const out = (await (await confirmed).json()) as { data: { status: string; result_refs: { id?: string; table?: string }[] } };
      expect(out.data.status).toBe("executed");
      const taskId = out.data.result_refs.find((r) => r.id)?.id;
      expect(taskId).toBeTruthy();
      expect((await page.request.get(`/api/backend/work/tasks/${taskId}`)).status()).toBe(200);
      await expect(page.getByTestId("undo-toast")).toBeVisible();
      await page.getByTestId("undo-toast-action").click();
      await expect(card).toHaveAttribute("data-status", "undone");
      expect((await page.request.get(`/api/backend/work/tasks/${taskId}`)).status()).toBe(404);
    });
  });
});

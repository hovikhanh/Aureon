import { expect, request, test, type Page } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { randomUUID } from "node:crypto";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { devPassword, login } from "./helpers";
import { cleanupReviewDocs, rootEnv, seedReviewDoc } from "./support/seed";
import { expireAccessToken } from "./support/session";

/**
 * T-618 / TC-M12-19 — M1.2 exit on the seeded stack (API :4000 + web :3000 + Mailpit :8025):
 * ADM creates a department and assigns an employee from today → CEO sees it on `/admin/org`;
 * a past `as_of` shows the old structure; ADM locks a user → that user is signed out on the
 * next refresh; EMP gets `/403` (page) and `403` (API); a notification e-mail reaches Mailpit.
 * `@real-only`: writes to the dev DB — `support/org_e2e.py --cleanup` restores it.
 */
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../..");
const MAILPIT = process.env.E2E_MAILPIT_URL ?? "http://localhost:8025";
const CODE = `E2E-${Date.now().toString(36).toUpperCase()}`;
const EMP_CODE = "NV-0153"; // ADM dept, manages nobody — safe to move for the test

function orgCleanup(): void {
  execFileSync(path.join(ROOT, ".venv/bin/python"), [path.join(ROOT, "apps/web/e2e/support/org_e2e.py"), "--cleanup"], {
    cwd: ROOT, env: { ...process.env, ...rootEnv(), PYTHONPATH: "apps/api/src:apps/api" }, encoding: "utf8", timeout: 60_000,
  });
}

async function logout(page: Page): Promise<void> {
  await page.goto("/home");
  await page.getByTestId("avatar").click();
  await page.getByTestId("logout").click();
  await expect(page).toHaveURL(/\/login/);
}

const API = process.env.E2E_API_URL ?? "http://localhost:4000/api/v1";

/** Unlock `email` straight on the API with an ADM token (cleanup must not depend on a browser). */
async function ensureActive(email: string): Promise<void> {
  const api = await request.newContext();
  try {
    const login = await api.post(`${API}/auth/login`, { data: { email: "admin@abc.demo", password: devPassword("admin@abc.demo") } });
    const auth = { authorization: `Bearer ${(await login.json()).data.access_token as string}` };
    const list = await api.get(`${API}/platform/users?q=${encodeURIComponent(email)}&limit=5`, { headers: auth });
    const u = ((await list.json()).data as { id: string; email: string; is_active: boolean }[]).find((x) => x.email === email);
    if (u && !u.is_active) {
      const res = await api.post(`${API}/platform/users/${u.id}/reactivate`, {
        headers: { ...auth, "idempotency-key": randomUUID() }, data: { reason: "E2E T-618 mở khóa" },
      });
      if (!res.ok()) throw new Error(`reactivate ${email}: ${res.status()}`);
    }
  } finally {
    await api.dispose();
  }
}

/** Users list through the BFF (session of the signed-in page). */
async function userByEmail(page: Page, email: string): Promise<{ id: string; is_active: boolean }> {
  const res = await page.request.get(`/api/backend/platform/users?q=${encodeURIComponent(email)}&limit=5`);
  expect(res.ok()).toBeTruthy();
  const row = ((await res.json()).data as { id: string; email: string; is_active: boolean }[]).find((u) => u.email === email);
  if (!row) throw new Error(`${email} not found`);
  return row;
}

test.describe("M1.2 org admin on the real stack (TC-M12-19)", { tag: "@real-only" }, () => {
  test.describe.configure({ mode: "serial" });
  test.beforeAll(async () => {
    orgCleanup();
    await ensureActive("office@abc.demo"); // a crashed earlier run may have left it locked
  });
  test.afterAll(async () => {
    orgCleanup();
    await ensureActive("office@abc.demo");
  });

  test("ADM creates a department + assigns an employee; CEO sees it; past as_of = old structure", async ({ page }) => {
    await login(page, "admin@abc.demo");
    await page.goto("/admin/org");
    await expect(page.getByTestId("org-tree")).toBeVisible();
    await page.getByTestId("org-new-dept").click();
    await page.getByTestId("dept-code").fill(CODE);
    await page.getByTestId("dept-name").fill("Phòng E2E");
    await page.getByTestId("dept-form-submit").click();
    await expect(page.getByTestId(`org-node-${CODE}`)).toBeVisible();

    await page.getByTestId("org-node-ADM").click();
    await page.getByTestId("dept-members").getByText(EMP_CODE).click();
    await page.getByTestId("emp-transfer").click();
    await page.getByTestId("assign-dept").selectOption({ label: `${CODE} — Phòng E2E` });
    await page.getByTestId("assign-reason").fill("E2E T-618");
    await page.getByTestId("assign-form-submit").click();
    await expect(page.getByTestId("assign-form")).toHaveCount(0);
    await logout(page);

    await login(page, "ceo@abc.demo");
    await page.goto("/admin/org");
    await page.getByTestId(`org-node-${CODE}`).click();
    await expect(page.getByTestId("dept-members")).toContainText(EMP_CODE);
    await expect(page.getByTestId("dept-archive")).toBeVisible(); // CEO has hr:admin
    // yesterday the department did not exist and the employee was still in ADM
    const yesterday = new Date(Date.now() - 86_400_000).toISOString().slice(0, 10); // API day = UTC
    await page.getByTestId("org-as-of").fill(yesterday);
    await expect(page.getByTestId("org-past-banner")).toBeVisible();
    await expect(page.getByTestId(`org-node-${CODE}`)).toHaveCount(0);
    await expect(page.getByTestId("org-new-dept")).toHaveCount(0);
    await page.getByTestId("org-node-ADM").click();
    await expect(page.getByTestId("dept-members")).toContainText(EMP_CODE);
    // the seeded transfer (T-617): NV-0049 was in Sales on 2023-06-01
    await page.getByTestId("org-as-of").fill("2023-06-01");
    await page.getByTestId("org-node-SAL").click();
    await expect(page.getByTestId("dept-members")).toContainText("NV-0049");
  });

  test("EMP: /admin/org → 403 page and the API answers 403", async ({ page }) => {
    await login(page, "employee@abc.demo");
    await page.goto("/admin/org");
    await expect(page.getByTestId("forbidden")).toBeVisible();
    const api = await page.request.get("/api/backend/org/tree");
    expect(api.status()).toBe(403);
    expect((await api.json()).error.code).toBe("FORBIDDEN_SCOPE"); // EMP holds hr:read, not the structure scope
  });

  test("ADM locks a user → that user is signed out on the next refresh; unlock restores login", async ({ browser }) => {
    test.setTimeout(120_000);
    const victimCtx = await browser.newContext();
    const victim = await victimCtx.newPage();
    await login(victim, "office@abc.demo");
    await expect(victim).toHaveURL(/\/home$/);

    const adminCtx = await browser.newContext();
    const admin = await adminCtx.newPage();
    await login(admin, "admin@abc.demo");
    await admin.goto("/admin/users");
    const row = admin.getByTestId("user-row").filter({ hasText: "office@abc.demo" });
    try {
      await row.getByTestId("user-lock").click();
      await admin.getByTestId("user-lock-dialog-reason").fill("E2E T-618 khóa thử");
      await admin.getByTestId("user-lock-dialog-confirm").click();
      await expect(admin.getByText(/phiên đăng nhập của người này đã bị thu hồi/)).toBeVisible();
      await expect(row).toHaveAttribute("data-active", "false");

      // access token ages out (≤ 15 min) → the refresh is refused → back to /login
      await expireAccessToken(victimCtx);
      await victim.reload();
      await expect(victim).toHaveURL(/\/login/, { timeout: 20_000 });
      await victim.goto("/login"); // locked → login refused (EP-ADM-09: 401 INVALID_CREDENTIALS)
      await victim.getByLabel("Email").fill("office@abc.demo");
      await victim.getByLabel(/^(Mật khẩu|Password)$/).fill(devPassword("office@abc.demo"));
      await victim.getByRole("button", { name: /Đăng nhập|Sign in/ }).click();
      await expect(victim.getByTestId("login-error")).toBeVisible();
      await expect(victim).toHaveURL(/\/login/);
    } finally {
      await ensureActive("office@abc.demo");
    }
    await login(victim, "office@abc.demo");
    await expect(victim).toHaveURL(/\/home$/);
    await victimCtx.close();
    await adminCtx.close();
  });

  test("a notification e-mail reaches Mailpit; the bell shows it", async ({ page }) => {
    test.setTimeout(240_000);
    const doc = seedReviewDoc();
    try {
      await login(page, "admin@abc.demo"); // ADM reads users (platform:admin)
      const reviewer = await userByEmail(page, "reviewer@abc.demo");
      await logout(page);
      // office@ = MGR of the reviewer's department → holds idp:approve and sees the doc (EP-126)
      await login(page, "office@abc.demo");
      const res = await page.request.post(`/api/backend/idp/documents/${doc.document_id}/review/reassign`, {
        headers: { "idempotency-key": randomUUID() }, data: { to_user_id: reviewer.id, reason: "E2E T-618" },
      });
      expect(res.ok()).toBeTruthy();
      await logout(page);
      const since = Date.now() - 5_000;
      // beat sweeps PENDING e-mails every NOTIFICATION_EMAIL_INTERVAL_SECONDS (60 s)
      await expect.poll(async () => {
        const r = await page.request.get(`${MAILPIT}/api/v1/search?query=${encodeURIComponent("to:reviewer@abc.demo")}&limit=5`);
        const msgs = ((await r.json()).messages ?? []) as { Subject: string; Created: string }[];
        return msgs.some((m) => Date.parse(m.Created) >= since && /review/i.test(m.Subject));
      }, { timeout: 150_000, intervals: [5_000] }).toBe(true);

      await login(page, "reviewer@abc.demo");
      await expect(page.getByTestId("notification-badge")).toBeVisible();
      await page.getByTestId("notification-bell").click();
      await expect(page.getByTestId("notification-item").first()).toContainText(/duyệt|review/i);
      await page.getByTestId("notification-read-all").click();
      await expect(page.getByTestId("notification-badge")).toHaveCount(0);
    } finally {
      cleanupReviewDocs();
    }
  });
});

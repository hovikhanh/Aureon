import { expect, test } from "./fixtures";
import { login } from "./helpers";

/**
 * M1.6 FE on mock (T-644F/T-646F/T-647F/T-645F): TC-M16-16 route guard + KillSwitchBanner, TC-M16-20
 * SCR-64 tabs, TC-M16-21 SCR-65 logs, TC-M16-19 ActionCard + UndoToast. `@mock-only`: mock store is
 * deterministic (seed: 4 AI actions, 36 log rows); the real-stack flow is T-649.
 */
test.describe("M1.6 AI Control Center (TC-M16-16/19/20/21)", { tag: ["@mock", "@mock-only"] }, () => {
  test("route guard: MGR → 403 page; kill switch API 403", async ({ page }) => {
    await login(page, "manager@abc.demo");
    for (const p of ["/admin/ai", "/admin/ai/logs", "/admin/onboarding"]) {
      await page.goto(p);
      await expect(page.getByTestId("forbidden")).toBeVisible();
    }
    expect((await page.request.get("/api/backend/ai/agents")).status()).toBe(200); // MGR holds ai:query
    expect((await page.request.put("/api/backend/ai/kill-switch", { headers: { "Idempotency-Key": `e2e-ks-${Date.now()}` }, data: { enabled: true, mode: "L0", reason: "x" } })).status()).toBe(403);
  });

  test("ADM: overview → kill switch on (WRITE_OFF) → banner for everyone → off", async ({ page }) => {
    await login(page, "admin@abc.demo");
    await page.goto("/admin");
    await page.getByTestId("admin-card-ai").click();
    await expect(page.getByTestId("ai-admin")).toBeVisible();
    await expect(page.getByTestId("kill-switch-banner")).toHaveCount(0);
    await expect(page.getByTestId("queue-count")).toHaveText("3");
    await page.getByTestId("kill-on").click();
    await page.getByTestId("kill-submit").click();
    await expect(page.getByTestId("kill-dialog")).toContainText(/lý do|reason/i);
    await page.getByTestId("kill-reason-input").fill("Sự cố dữ liệu");
    await page.getByTestId("kill-submit").click();
    const banner = page.getByTestId("kill-switch-banner");
    await expect(banner).toBeVisible();
    await expect(banner).toHaveAttribute("role", "status");
    await expect(banner).toHaveAttribute("aria-live", "polite");
    await expect(banner).toContainText("AI đang tạm dừng ghi dữ liệu");
    await expect(page.getByTestId("kill-switch-link")).toBeVisible();

    await page.getByTestId("kill-off").click();
    await page.getByTestId("kill-reason-input").fill("Đã xử lý");
    await page.getByTestId("kill-submit").click();
    await expect(banner).toHaveCount(0);
  });

  test("banner L0 for an employee, without the admin link", async ({ page }) => {
    await login(page, "admin@abc.demo");
    const res = await page.request.put("/api/backend/ai/kill-switch", { headers: { "Idempotency-Key": `e2e-ks-${Date.now()}` }, data: { enabled: true, mode: "L0", agents: [], reason: "e2e" } });
    expect(res.status()).toBe(200);
    await page.context().clearCookies(); // logout (as capture.spec): /login redirects a signed-in user
    await login(page, "employee@abc.demo");
    await expect(page.getByTestId("kill-switch-text")).toHaveText("AI chỉ trả lời, không soạn thao tác");
    await expect(page.getByTestId("kill-switch-link")).toHaveCount(0);
  });

  test("tabs: agents (L3 disabled), autonomy (struck L3), tool registry (53 tools, filter, expand)", async ({ page }) => {
    await login(page, "ceo@abc.demo");
    await page.goto("/admin/ai?tab=agents");
    await expect(page.getByTestId("agent-row")).toHaveCount(6);
    await page.getByTestId("agent-edit").first().click();
    await expect(page.getByTestId("agent-level-L3")).toBeDisabled();
    await expect(page.getByTestId("agent-level-L4")).toBeDisabled();
    await page.keyboard.press("Escape");

    await page.getByTestId("ai-tab-autonomy").click();
    await expect(page.getByTestId("matrix-row").first()).toBeVisible();
    await page.getByTestId("policy-new").click();
    await page.getByTestId("policy-level").selectOption("L3");
    await page.getByTestId("policy-max_level").selectOption("L3");
    await page.getByTestId("policy-reason").fill("thử");
    await page.getByTestId("policy-save").click();
    await expect(page.getByTestId("policy-error")).toContainText("Vượt trần tự chủ M1");
    await page.keyboard.press("Escape");

    await page.getByTestId("ai-tab-tools").click();
    await expect(page.getByTestId("tool-row")).toHaveCount(53);
    await page.getByTestId("tool-filter-kind").selectOption("EXECUTION");
    const rows = await page.getByTestId("tool-row").count();
    expect(rows).toBeLessThan(53);
    await page.getByTestId("tool-expand").first().click();
    await expect(page.getByTestId("tool-input-schema")).toBeVisible();
  });

  test("SCR-65: tool call drawer, request_id filter, model call cost, cost tab", async ({ page }) => {
    await login(page, "admin@abc.demo");
    await page.goto("/admin/ai/logs");
    await expect(page.getByTestId("tool-call-row").first()).toBeVisible();
    await page.getByTestId("tool-call-row").first().click();
    await expect(page.getByTestId("tool-call-args")).toBeVisible();
    await page.keyboard.press("Escape");
    await page.getByTestId("log-request-id").first().click();
    await expect(page.getByTestId("logs-audit-link")).toHaveAttribute("href", /request_id=/);
    await expect(page.getByTestId("tool-call-row")).not.toHaveCount(0);
    await page.getByTestId("logs-tab-model").click();
    await expect(page.getByTestId("model-cost").first()).toHaveText(/^\$\d+\.\d{4}$/);
    await page.getByTestId("logs-tab-cost").click();
    await page.getByTestId("cost-group").selectOption("model");
    await expect(page.getByTestId("cost-row").first()).toBeVisible();
  });

  test("ActionCard in /ask: CEO confirms an L2 card → UndoToast → undo", async ({ page }) => {
    await login(page, "ceo@abc.demo");
    await page.goto("/ask");
    await page.getByTestId("chat-input").fill("Tạo task gọi lại khách hàng ABC");
    await page.getByTestId("chat-send").click();
    const card = page.getByTestId("action-card");
    await expect(card).toBeVisible();
    await expect(page.getByTestId("action-level")).toHaveText("AI soạn");
    await page.getByTestId("action-confirm").click();
    await expect(page.getByTestId("undo-toast")).toBeVisible();
    await page.getByTestId("undo-toast-action").click();
    await expect(page.getByTestId("undo-toast")).toHaveCount(0);
    await expect(card).toHaveAttribute("data-status", "undone");
  });

  test("ADM sees the queue but cannot confirm (not on_behalf_of)", async ({ page }) => {
    await login(page, "admin@abc.demo");
    await page.goto("/admin/ai");
    await expect(page.getByTestId("ai-queue").getByTestId("action-card")).toHaveCount(3);
    await expect(page.getByTestId("action-confirm")).toHaveCount(0);
  });
});

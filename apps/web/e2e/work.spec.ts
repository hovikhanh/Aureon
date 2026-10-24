import { execFileSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test, type Browser, type Locator, type Page } from "./fixtures";
import { login } from "./helpers";
import { rootEnv } from "./support/seed";

/**
 * T-625F / TC-M13-12 — M1.3 work screens on the mock BFF (API_MODE=mock): tabs per role,
 * SCR-42 due groups + filters in the query string, kanban status change (keyboard + drag, rule
 * failure snaps back), SCR-55 late flag, SCR-56 milestones, SCR-57 heatmap + overload badge,
 * SCR-43 approve / reject (reason required), EMP → /403. `@mock-only`: the mock store is
 * deterministic and relative to the business date; the real-stack flow is T-625 (TC-M13-13).
 */
const tabs = (page: Page) => page.getByTestId("work-tabs").getByRole("link");

/** HTML5 drag-and-drop with a shared DataTransfer (deterministic in headless Chromium). */
async function dragCard(page: Page, card: Locator, column: Locator): Promise<void> {
  const dataTransfer = await page.evaluateHandle(() => new DataTransfer());
  await card.dispatchEvent("dragstart", { dataTransfer });
  await column.dispatchEvent("dragover", { dataTransfer });
  await column.dispatchEvent("drop", { dataTransfer });
  await card.dispatchEvent("dragend", { dataTransfer });
}

test.describe("M1.3 work screens (TC-M13-12)", { tag: ["@mock", "@mock-only"] }, () => {
  test("EMP: my tasks grouped by due, filters in URL, FR-TASK-02 toast, no team/workload/approvals", async ({ page }) => {
    await login(page, "employee@abc.demo");
    await page.goto("/work");
    await expect(tabs(page)).toHaveCount(2);
    await expect(page.getByTestId("work-tab-mine")).toHaveAttribute("aria-current", "page");
    await expect(page.getByTestId("work-tab-board")).toHaveCount(0);
    for (const g of ["overdue", "today", "week", "none"]) await expect(page.getByTestId(`group-${g}`)).toBeVisible();
    const today = page.getByTestId("group-today").getByTestId(/^task-row-/).first();
    await expect(today.getByTestId("task-source-chip")).toHaveAttribute("data-kind", "document");
    await expect(today.getByTestId("task-blocked-by")).toBeVisible();
    await expect(page.getByTestId("group-overdue").getByTestId("task-due").first()).toHaveClass(/text-danger/);

    // done blocked by an open dependency → toast naming the blocker, row stays put
    await today.getByTestId(/^move-/).click();
    await page.getByTestId("move-to-done").click();
    await expect(page.getByText(/Chưa thể hoàn thành/)).toContainText("Gọi lại khách hàng");
    await expect(page.getByTestId("group-today").getByTestId(/^task-row-/).first()).toHaveAttribute("data-status", "todo");

    // filters → query string (status CSV + due range), survive reload
    await page.getByTestId("status-done").click();
    await expect(page).toHaveURL(/status=backlog%2Ctodo%2Cin_progress%2Cblocked%2Cin_review%2Cdone/);
    await page.getByTestId("status-backlog").click();
    await expect(page.getByTestId("group-none")).toHaveCount(0);
    await page.getByTestId("due-from").fill("2030-01-02");
    await expect(page).toHaveURL(/due_from=2030-01-02/);
    await page.getByTestId("due-to").fill("2030-01-01");
    await expect(page.getByTestId("range-invalid")).toBeVisible();
    await page.reload();
    await expect(page.getByTestId("due-from")).toHaveValue("2030-01-02");
    await page.getByTestId("clear-filters").click();
    await expect(page).toHaveURL(/\/work$/);

    // detail panel ?task= + reassign request (manual employee-ID fallback: EMP cannot read /org/tree)
    await page.getByTestId("group-week").getByRole("button", { name: "Mở chi tiết Chuẩn bị báo cáo tuần bộ phận CSKH" }).click();
    await expect(page).toHaveURL(/task=/);
    await page.getByTestId("task-tab-subtasks").click();
    await expect(page.getByTestId("task-subtasks-panel")).toContainText("Tổng hợp số phiếu");
    await page.getByTestId("task-tab-info").click();
    await page.getByTestId("request-reassign").click();
    await page.getByTestId("reassign-to-id").fill("NV-0049");
    await page.getByTestId("reassign-submit").click();
    await expect(page.getByTestId("reassign-dialog")).toContainText(/ID nhân viên chưa hợp lệ/);
    await expect(page.getByTestId("reassign-dialog")).toContainText(/Vui lòng nhập lý do/);
    await page.keyboard.press("Escape");

    for (const denied of ["/work/workload", "/work/approvals"]) {
      await page.goto(denied);
      await expect(page.getByTestId("forbidden")).toBeVisible();
    }
    await page.goto("/work?view=board");
    await expect(page.getByTestId("my-tasks")).toBeVisible();
  });

  test("MGR: kanban — assign, keyboard move, wrong rule snaps back, drag to column", async ({ page }) => {
    await login(page, "manager@abc.demo");
    await page.goto("/work");
    await expect(tabs(page)).toHaveCount(5);
    await page.getByTestId("work-tab-board").click();
    await expect(page).toHaveURL(/view=board/);
    await expect(page.getByTestId("board-dept")).toBeDisabled();
    await expect(page.getByTestId("col-cancelled")).toHaveCount(0);

    const title = `E2E kanban ${Date.now().toString(36)}`;
    await page.getByTestId("board-assign").click();
    await page.getByTestId("ct-title").fill(title);
    await page.getByTestId("ct-assignee").selectOption({ label: "NV-0046 · Ngô Thị Lan" });
    await page.getByTestId("ct-submit").click();
    const card = page.getByTestId(/^card-/).filter({ hasText: title });
    await expect(page.getByTestId("col-todo").getByText(title)).toBeVisible();

    // keyboard path: "Chuyển sang…" menu
    await card.getByTestId(/^card-move-/).focus();
    await page.keyboard.press("Enter");
    await page.getByTestId("move-to-in_progress").click();
    await expect(page.getByTestId("col-in_progress").getByText(title)).toBeVisible();

    // drag to a column the rule forbids (in_progress → backlog) → toast, card snaps back
    await dragCard(page, card, page.getByTestId("col-backlog"));
    await expect(page.getByText("Không thể chuyển trạng thái này.")).toBeVisible();
    await expect(page.getByTestId("col-in_progress").getByText(title)).toBeVisible();
    // stale version (someone else edited the card) → 409 toast, board reloads, card stays
    const cardId = (await card.getAttribute("data-testid"))!.replace("card-", "");
    const bump = await page.request.patch(`/api/backend/work/tasks/${cardId}`, { data: { description: "edited elsewhere", version: 2 } });
    expect(bump.status()).toBe(200);
    await dragCard(page, card, page.getByTestId("col-in_review"));
    await expect(page.getByText("Dữ liệu đã thay đổi. Vui lòng tải lại.")).toBeVisible();
    await expect(page.getByTestId("col-in_progress").getByText(title)).toBeVisible();
    // allowed drag (fresh version after reload) → in_review
    await dragCard(page, card, page.getByTestId("col-in_review"));
    await expect(page.getByTestId("col-in_review").getByText(title)).toBeVisible();

    await page.getByTestId("board-show-cancelled").click();
    await expect(page.getByTestId("col-cancelled")).toBeVisible();
  });

  test("CEO: projects late flag → detail milestones; workload overload badge", async ({ page }) => {
    await login(page, "ceo@abc.demo");
    await page.goto("/work/projects");
    await expect(page.getByTestId("projects-table")).toBeVisible();
    const lateRows = page.locator("[data-testid^=project-row-][data-late=true]");
    await expect(lateRows.first().getByTestId("project-late")).toBeVisible();
    const total = await page.locator("[data-testid^=project-row-]").count();
    await page.getByTestId("projects-late").click();
    await expect.poll(() => page.locator("[data-testid^=project-row-]").count()).toBeLessThan(total);
    await expect(page.locator("[data-testid^=project-row-][data-late=false]")).toHaveCount(0);

    await page.getByTestId("project-row-PRJ-ERP").getByRole("link").first().click();
    await expect(page.getByTestId("project-detail")).toBeVisible();
    await expect(page.getByTestId("project-detail").getByRole("navigation", { name: "Công việc" })).toContainText("PRJ-ERP");
    await expect(page.locator("[data-testid^=milestone-][data-late=true]").first()).toBeVisible();
    await page.getByTestId("ms-title").fill("Nghiệm thu E2E");
    await page.getByTestId("ms-due").fill("2027-03-31");
    await page.getByTestId("ms-add").click();
    await expect(page.getByTestId("milestones")).toContainText("Nghiệm thu E2E");
    await page.getByTestId("project-tab-tasks").click();
    await expect(page.getByTestId("project-tasks").getByTestId(/^task-row-/).first()).toBeVisible();

    await page.getByTestId("work-tab-workload").click();
    await expect(page.getByTestId("wl-table")).toBeVisible();
    await expect(page.getByTestId("wl-summary-text")).toContainText(/^3\//);
    await expect(page.getByTestId("wl-overloaded")).toHaveCount(3);
    const first = page.locator("[data-testid^=wl-row-]").first();
    await expect(first).toHaveAttribute("data-overloaded", "true");
    await expect(first.locator("[data-shade=high]").last()).toContainText("%");
    await first.locator("[data-testid^=wl-cell-]").last().click();
    await expect(page.getByTestId("wl-cell-dialog")).toBeVisible();
  });

  test("MGR approves the EMP reassign request (SCR-43)", async ({ page }) => {
    await login(page, "manager@abc.demo");
    await page.goto("/work/approvals");
    await expect(page.getByTestId("approvals-badge")).toBeVisible();
    const req = page.locator("[data-testid^=approval-][data-kind=task_reassign]").first();
    // BE shape: title_key `approval.task_reassign.title` + ids-only params → names from members[]
    await expect(req).toContainText(/Chuyển việc từ Ngô Thị Lan sang \S/);
    await req.click();
    await expect(page.getByTestId("approval-diff")).toContainText("assignee_id");
    await expect(page).toHaveURL(/[?&]id=/);
    await expect(page.getByTestId("approval-diff")).toContainText("Ngô Thị Lan");
    await page.getByTestId("approval-approve").click();
    await page.getByTestId("approve-dialog-confirm").click();
    await expect(page.getByText("Đã duyệt yêu cầu.")).toBeVisible();
    await expect(page.locator("[data-testid^=approval-][data-kind=task_reassign]")).toHaveCount(0);
  });

  test("DIR finance rejects an AI action only with a reason (SCR-43)", async ({ page }) => {
    await login(page, "cfo@abc.demo");
    await page.goto("/work/approvals");
    const ai = page.locator("[data-testid^=approval-][data-kind=ai_action]");
    await expect(ai.first().getByTestId("approval-amount")).toContainText(/tỷ|triệu/);
    await expect(ai.getByTestId("approval-due").and(page.locator(".text-danger"))).toHaveCount(1);
    await expect(ai.first()).toContainText("Hành động AI cần duyệt");
    await ai.filter({ has: page.locator("[data-testid=approval-due]:not(.text-danger)") }).click();
    await expect(page.getByTestId("approval-diff")).toContainText("Sài Gòn");
    await page.getByTestId("approval-reject").click();
    await page.getByTestId("reject-dialog-confirm").click();
    await expect(page.getByTestId("reject-dialog-error")).toBeVisible();
    await page.getByTestId("reject-dialog-reason").fill("Chưa đủ chứng từ");
    await page.getByTestId("reject-dialog-confirm").click();
    await expect(page.getByText("Đã từ chối yêu cầu.")).toBeVisible();
    await expect(ai).toHaveCount(1);
  });
});

/**
 * T-625 / TC-M13-10, TC-M13-13 — M1.3 exit on the real stack (API + web + Celery beat + Mailpit):
 * MGR assigns a task to Ngô Thị Lan (= employee@) → EMP sees it in "Task của tôi", the bell has
 * `task_assigned` (link `/work?task=` opens the panel) and the e-mail reaches Mailpit; EMP asks to
 * reassign (manual employee ID — EMP cannot read EP-ORG-24) → MGR opens the `approval_requested`
 * notification (`/work/approvals?id=`) and approves → the task changes assignee; EMP gets `/403` on
 * workload / approvals; the heatmap shows 3 overloaded people (seed, METRIC-HR-03 — company-wide,
 * so read as CEO: MGR SVC has none). `@real-only`: writes to the dev DB — `support/work_e2e.py`.
 */
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../..");
const MAILPIT = process.env.E2E_MAILPIT_URL ?? "http://localhost:8025";

function workCleanup(): void {
  execFileSync(path.join(ROOT, ".venv/bin/python"), [path.join(ROOT, "apps/web/e2e/support/work_e2e.py"), "--cleanup"], {
    cwd: ROOT, env: { ...process.env, ...rootEnv(), PYTHONPATH: "apps/api/src:apps/api" }, encoding: "utf8", timeout: 60_000,
  });
}

async function session(browser: Browser, email: string): Promise<Page> {
  const page = await (await browser.newContext()).newPage();
  await login(page, email);
  return page;
}

type Member = { employee_id: string; employee_code: string; full_name: string };
async function member(page: Page, code: string): Promise<Member> {
  const res = await page.request.get("/api/backend/org/tree");
  expect(res.ok()).toBeTruthy();
  const all = ((await res.json()).data.departments as { members: Member[] }[]).flatMap((d) => d.members);
  const m = all.find((x) => x.employee_code === code);
  if (!m) throw new Error(`${code} not in /org/tree`);
  return m;
}

test.describe("M1.3 work flow on the real stack (TC-M13-10/13)", { tag: "@real-only" }, () => {
  test.describe.configure({ mode: "serial" });
  test.beforeAll(() => workCleanup());
  test.afterAll(() => workCleanup());

  test("assign → EMP sees + notified + e-mail; reassign request → MGR approves; EMP /403", async ({ browser }) => {
    test.setTimeout(300_000);
    const title = `E2E work ${Date.now().toString(36)}`;
    const since = Date.now() - 5_000;

    // MGR (SVC) assigns from the kanban
    const mgr = await session(browser, "manager@abc.demo");
    const lan = await member(mgr, "NV-0046");
    const phuc = await member(mgr, "NV-0045");
    await mgr.goto("/work?view=board");
    await mgr.getByTestId("board-assign").click();
    await mgr.getByTestId("ct-title").fill(title);
    await mgr.getByTestId("ct-assignee").selectOption(lan.employee_id);
    await mgr.getByTestId("ct-submit").click();
    await expect(mgr.getByTestId("col-todo").getByText(title)).toBeVisible();

    // EMP: "Task của tôi" (mine=true) + bell → /work?task=<id>
    const emp = await session(browser, "employee@abc.demo");
    await emp.goto("/work");
    const row = emp.getByTestId("my-tasks").getByTestId(/^task-row-/).filter({ hasText: title });
    await expect(row).toBeVisible();
    const taskId = (await row.getAttribute("data-testid"))!.replace("task-row-", "");
    await expect(emp.getByTestId("notification-badge")).toBeVisible();
    await emp.getByTestId("notification-bell").click();
    await emp.getByTestId("notification-item").filter({ hasText: "Bạn được giao việc mới" }).first().click();
    await expect(emp).toHaveURL(new RegExp(`/work\\?task=${taskId}`));
    await expect(emp.getByTestId("task-detail-title")).toHaveText(title);

    // TC-M13-10: the task_assigned e-mail reaches Mailpit (beat sweep)
    await expect.poll(async () => {
      const r = await emp.request.get(`${MAILPIT}/api/v1/search?query=${encodeURIComponent("to:employee@abc.demo")}&limit=10`);
      const msgs = ((await r.json()).messages ?? []) as { Subject: string; Created: string }[];
      return msgs.some((m) => Date.parse(m.Created) >= since && m.Subject.includes("Bạn được giao việc mới"));
    }, { timeout: 150_000, intervals: [5_000] }).toBe(true);

    // EMP asks to reassign to Hoàng Minh Phúc — ID typed in (no picker for EMP, OQ-13-09)
    await emp.getByTestId("request-reassign").click();
    await expect(emp.getByTestId("reassign-to")).toHaveCount(0);
    await emp.getByTestId("reassign-to-id").fill(phuc.employee_id);
    await emp.getByTestId("reassign-reason").fill("E2E T-625 dồn việc bảo trì");
    await emp.getByTestId("reassign-submit").click();
    await expect(emp.getByText("Đã gửi đề nghị chuyển người cho quản lý.")).toBeVisible();
    for (const denied of ["/work/workload", "/work/approvals"]) {
      await emp.goto(denied);
      await expect(emp.getByTestId("forbidden")).toBeVisible();
    }

    // MGR: approval_requested → /work/approvals?id=<id> → approve → task moves to Phúc
    await mgr.goto("/work");
    await mgr.getByTestId("notification-bell").click();
    await mgr.getByTestId("notification-item").filter({ hasText: "Có yêu cầu chờ bạn duyệt" }).first().click();
    await expect(mgr).toHaveURL(/\/work\/approvals\?id=/);
    await expect(mgr.getByTestId("approval-title")).toHaveText(`Chuyển việc từ ${lan.full_name} sang ${phuc.full_name}`);
    await expect(mgr.getByTestId("approval-diff")).toContainText(phuc.full_name);
    await expect(mgr.getByTestId("approvals-badge")).toBeVisible();
    await mgr.getByTestId("approval-approve").click();
    await mgr.getByTestId("approve-dialog-confirm").click();
    await expect(mgr.getByText("Đã duyệt yêu cầu.")).toBeVisible();
    const task = await mgr.request.get(`/api/backend/work/tasks/${taskId}`);
    expect((await task.json()).data.assignee_id).toBe(phuc.employee_id);
    await emp.goto("/work");
    await expect(emp.getByTestId("my-tasks").getByText(title)).toHaveCount(0);
    await emp.context().close();
    await mgr.context().close();
  });

  test("workload heatmap: 3 overloaded people with a badge (seed, METRIC-HR-03)", async ({ page }) => {
    await login(page, "ceo@abc.demo");
    await page.goto("/work/workload");
    await expect(page.getByTestId("wl-table")).toBeVisible();
    await expect(page.getByTestId("wl-summary-text")).toContainText(/^3\//);
    await expect(page.getByTestId("wl-overloaded")).toHaveCount(3);
    await expect(page.locator("[data-testid^=wl-row-][data-overloaded=true]")).toHaveCount(3);
  });
});

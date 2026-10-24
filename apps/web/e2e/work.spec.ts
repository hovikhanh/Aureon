import { expect, test, type Locator, type Page } from "@playwright/test";
import { login } from "./helpers";

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
    await expect(req).toContainText("Chuyển “Đề xuất cải tiến quy trình tiếp nhận”");
    await req.click();
    await expect(page.getByTestId("approval-diff")).toContainText("assignee_id");
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
    await ai.filter({ hasText: "Sài Gòn" }).click();
    await page.getByTestId("approval-reject").click();
    await page.getByTestId("reject-dialog-confirm").click();
    await expect(page.getByTestId("reject-dialog-error")).toBeVisible();
    await page.getByTestId("reject-dialog-reason").fill("Chưa đủ chứng từ");
    await page.getByTestId("reject-dialog-confirm").click();
    await expect(page.getByText("Đã từ chối yêu cầu.")).toBeVisible();
    await expect(ai).toHaveCount(1);
  });
});

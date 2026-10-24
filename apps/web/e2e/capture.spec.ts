import { expect, test, type Page } from "@playwright/test";
import { login } from "./helpers";

/**
 * T-634F..T-638F / T-643 (mock) — M1.5 Data Capture screens on the mock BFF (API_MODE=mock):
 * SCR-45 inbox (groups + `meta.counts`, MANUAL source → 422), SCR-61 C1 form (EMP task →
 * `/work/tasks`, UndoToast), SCR-62 C5 import (DOC-06 map → errors → submit) → SCR-18b REV
 * approve-pending → DIR khối O commits → `/admin/org` + LineageChip → undo; SCR-63 admin.
 * `@mock-only`: relies on the mock store seed (CAP-* documents, DOC-06 content by file name)
 * until the M1.5 BE lands (TC-M15-17/18 real-stack part).
 */
const DOC06 = "DOC-06-danh-sach-nhan-su.xlsx";
const XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

async function logout(page: Page): Promise<void> {
  await page.context().clearCookies();
}

test.describe("M1.5 data capture", { tag: ["@mock", "@mock-only"] }, () => {
  test("SCR-45: groups with counts, filters, MANUAL source → no file, history", async ({ page }) => {
    await login(page, "ceo@abc.demo");
    const made = await page.request.post("/api/backend/data-capture/manual", { headers: { "Idempotency-Key": `e2e-${Date.now()}` },
      data: { document_type: "PLAN_KPI_OKR", schema_version: 1, values: {}, rows: [{ task_title: "Việc E2E inbox", task_due_date: "30/11/2026" }] } });
    expect(made.status()).toBe(201);
    const doc = ((await made.json()) as { data: { document: { id: string } } }).data.document.id;
    await page.goto("/data");
    await expect(page.getByTestId("data-inbox")).toHaveAttribute("data-scr", "SCR-45");
    await expect(page.getByTestId("count-committed")).not.toHaveText("0");
    await page.getByTestId("group-committed").click();
    await page.getByTestId("filter-channel").selectOption("C1");
    const row = page.locator(`[data-testid="inbox-row"][data-doc="${doc}"]`);
    await expect(row).toBeVisible();
    await row.getByTestId("inbox-more").click();
    await expect(page.getByTestId("inbox-source")).toHaveCount(0); // MANUAL: no "Xem tài liệu gốc"
    await page.getByTestId("inbox-history").click();
    await expect(page.getByTestId("history-row").first()).toBeVisible();
    const src = await page.request.get(`/api/backend/data-capture/documents/${doc}/source`);
    expect([src.status(), ((await src.json()) as { error: { details: { reason: string } } }).error.details.reason]).toEqual([422, "no_file"]);
  });

  test("SCR-61: EMP enters a task (C1) → COMMITTED + UndoToast → task in /work with lineage", async ({ page }) => {
    await login(page, "employee@abc.demo");
    await page.goto("/data");
    await page.getByTestId("manual-menu").click();
    await page.getByTestId("manual-PLAN_KPI_OKR").click();
    await expect(page.getByTestId("schema-form")).toHaveAttribute("data-scr", "SCR-61");
    await page.getByTestId("field-rows-0-task_title").fill("Gọi lại khách hàng E2E");
    await page.getByTestId("field-rows-0-task_due_date").fill("31/13/2026");
    await page.getByTestId("form-submit").click();
    await expect(page.locator("#rows-0-task_due_date-err")).toBeVisible();
    await page.getByTestId("field-rows-0-task_due_date").fill("30/11/2026");
    await page.getByTestId("form-submit").click();
    const toast = page.getByTestId("undo-toast");
    await expect(toast).toBeVisible();
    await toast.hover(); // paused while hovered
    await page.waitForTimeout(500);
    await expect(toast).toBeVisible();
    await toast.getByRole("button", { name: "Đóng" }).click();
    await expect(page).toHaveURL(/\/data$/);
    await page.goto("/work");
    await page.getByRole("button", { name: /Gọi lại khách hàng E2E/ }).first().click();
    await expect(page.getByTestId("task-detail-title")).toHaveText("Gọi lại khách hàng E2E");
    await page.getByTestId("lineage-chip").click();
    await expect(page.getByTestId("lineage-popover")).toBeVisible();
    await expect(page.getByTestId("lineage-link").first()).toBeVisible();
  });

  test("SCR-62 → SCR-18b: hr@ imports DOC-06, REV approves pending, hr@ commits → org + lineage → undo", async ({ page }) => {
    test.setTimeout(240_000);
    await login(page, "hr@abc.demo");
    await page.goto("/data");
    await page.getByTestId("dropzone-input").setInputFiles({ name: DOC06, mimeType: XLSX, buffer: Buffer.from(`PK mock ${"x".repeat(Date.now() % 997)}`) });
    await page.getByTestId("dropzone-import").click();
    await expect(page).toHaveURL(/\/data\/imports\//);
    const wizard = page.getByTestId("import-wizard");
    await expect(wizard).toHaveAttribute("data-scr", "SCR-62");
    await expect(page.getByTestId("import-suggested")).toBeVisible();
    await expect(page.getByTestId("mapper-ai").first()).toBeVisible();
    const code = page.locator('[data-testid="mapper-row"][data-header="Mã NV"]').getByTestId("mapper-select");
    await code.selectOption("");
    await expect(page.getByTestId("unmapped-required")).toBeVisible();
    await expect(page.getByTestId("import-save-mapping")).toBeDisabled();
    await code.selectOption("employee_code");
    await page.getByTestId("import-save-mapping").click();
    await expect(wizard).toHaveAttribute("data-step", "preview");
    await expect(page.getByTestId("summary-valid")).toContainText("51");
    await expect(page.getByTestId("summary-invalid")).toContainText("1");
    await expect(page.locator('[data-testid="import-row"][data-invalid="true"]').first().getByTestId("cell-error").first()).toBeVisible();
    const dl = page.waitForEvent("download");
    await page.getByTestId("import-download-errors").click();
    expect((await dl).suggestedFilename()).toMatch(/\.xlsx$/);
    await page.getByTestId("import-next").click();
    await page.getByTestId("import-submit").click();
    await expect(page).toHaveURL(/\/data$/);
    const docId = await page.locator('[data-testid="inbox-row"][data-status="NEEDS_REVIEW"]').first().getAttribute("data-doc");
    expect(docId).toBeTruthy();

    await logout(page);
    await login(page, "reviewer@abc.demo");
    await page.goto(`/data/review/${docId}`);
    await expect(page.getByTestId("grid-row")).toHaveCount(25);
    await expect(page.locator('[data-testid="planned-action"][data-permitted="false"]')).toHaveCount(2);
    await expect(page.getByTestId("critical-left")).toContainText("51");
    await expect(page.getByTestId("approve")).toBeDisabled();
    await expect(page.getByTestId("approve")).toContainText("chờ người có quyền ghi");
    // confirm every critical (salary) field via the API, then reload — the grid walk is covered by the confirm-row unit path
    const detail = (await (await page.request.get(`/api/backend/idp/documents/${docId}/review`)).json()) as { data: { fields: { id: string; is_critical: boolean }[] } };
    await page.request.patch(`/api/backend/idp/documents/${docId}/fields`, { data: { fields: detail.data.fields.filter((f) => f.is_critical).map((f) => ({ field_id: f.id, action: "confirm" })) } });
    await page.reload();
    await page.getByTestId("grid-cell").first().click();
    await page.getByTestId("confirm-row").click();
    await page.getByTestId("approve").click();
    await expect(page).toHaveURL(/\/data\/review$/);

    await logout(page);
    await login(page, "hr@abc.demo");
    await page.goto(`/data/review/${docId}`);
    await expect(page.getByTestId("approved-state")).toBeVisible();
    await page.getByTestId("commit").click();
    await expect(page.getByTestId("undo-toast")).toBeVisible();
    await page.getByTestId("undo-toast").getByRole("button", { name: "Đóng" }).click();

    await page.goto("/admin/org");
    await page.getByTestId("org-node-OPS").click();
    await expect(page.getByTestId("dept-panel")).toBeVisible();
    await page.getByTestId("lineage-chip").first().click();
    await expect(page.getByTestId("lineage-link").first()).toContainText("Nhân sự");

    await page.goto("/data");
    await page.getByTestId("group-committed").click();
    const row = page.locator(`[data-testid="inbox-row"][data-doc="${docId}"]`);
    await row.getByTestId("inbox-undo").click();
    await page.getByTestId("undo-reason").fill("Nhập nhầm file");
    await page.getByTestId("undo-confirm").click();
    await expect(page.getByTestId("undo-dialog")).toHaveCount(0);
    await page.getByTestId("group-rolled_back").click();
    await expect(page.locator(`[data-testid="inbox-row"][data-doc="${docId}"]`)).toBeVisible();
  });

  test("SCR-63 admin (ADM): no incidents tab, schema draft guards, rules, publish", async ({ page }) => {
    await login(page, "admin@abc.demo", "unused-on-mock");
    await page.goto("/admin");
    await page.getByTestId("admin-card-dataCapture").click();
    await expect(page.getByTestId("capture-admin")).toHaveAttribute("data-scr", "SCR-63");
    await expect(page.getByTestId("admin-tab-incidents")).toHaveCount(0);
    await expect(page.locator('[data-testid="type-row"][data-code="HR_ROSTER"]')).toBeVisible();
    await page.getByTestId("admin-tab-schemas").click();
    await page.locator('[data-testid="schema-row"][data-type="HR_ROSTER"][data-status="published"]').getByTestId("schema-clone").click();
    await expect(page.getByTestId("schema-editor")).toBeVisible();
    await page.locator('[data-testid="schema-field"][data-name="salary"]').getByTestId("field-critical").click();
    await page.getByTestId("schema-save").click();
    await expect(page.getByTestId("schema-error")).toBeVisible();
    await expect(page.locator('[data-testid="schema-field"][data-name="salary"]')).toHaveClass(/bg-danger-subtle/);
    await page.locator('[data-testid="schema-field"][data-name="salary"]').getByTestId("field-critical").click();
    await page.getByTestId("th-class").fill("0,9");
    await page.getByTestId("schema-save").click();
    await expect(page.getByTestId("schema-error")).toBeVisible();
    await page.getByTestId("th-class").fill("0,96");
    await page.getByTestId("schema-save").click();
    await expect(page.getByTestId("schema-editor")).toHaveCount(0);
    await page.getByTestId("admin-tab-rules").click();
    await page.getByTestId("rule-code").fill("E2E_STATUS_IN");
    await page.getByTestId("rule-op").selectOption("in");
    await page.getByTestId("rule-field").selectOption("status");
    await page.getByTestId("rule-value").fill("ACTIVE, PROBATION");
    await page.getByTestId("rule-add").click();
    await expect(page.locator('[data-testid="rule-row"][data-code="E2E_STATUS_IN"]')).toBeVisible();
    await page.getByTestId("rule-code").fill("E2E_STATUS_IN");
    await page.getByTestId("rule-add").click();
    await expect(page.getByTestId("rule-error")).toBeVisible(); // duplicate code → 409 DUPLICATE_RESOURCE
    await page.getByTestId("admin-tab-schemas").click();
    await page.locator('[data-testid="schema-row"][data-type="HR_ROSTER"][data-status="draft"]').getByTestId("schema-publish").click();
    await expect(page.locator('[data-testid="schema-row"][data-type="HR_ROSTER"][data-status="retired"]')).toBeVisible();
  });
});

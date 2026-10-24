import { expect, test } from "./fixtures";
import { login, loginAs, loginWithPassword } from "./helpers";
import { cleanupReviewDocs, rootEnv, seedReviewDoc } from "./support/seed";

/**
 * T-516 regression across the demo roles, extended in T-609 (TC-M11-15) to the 7 v3 roles:
 * CEO, DIR (CFO, HR), MGR, EMP, REV, ADM here; ROLE-AI refusal in login.spec.
 */
test.afterAll(() => cleanupReviewDocs());

const SLUGS = { F: "finance", O: "operations", C: "customer", U: "product", S: "strategy" } as const;

test("CEO: F/O/C cards drill down, 5-pillar layout on SCR-03, 13 alerts", async ({ page }) => {
  await loginAs(page, "ceo@abc.demo");
  await expect(page.getByTestId("alert-row")).toHaveCount(13);
  for (const code of ["O", "C"] as const) {
    await expect(page.getByTestId(`pillar-${code}`)).toHaveAttribute("data-status", /ok|warning|critical/);
    await page.getByTestId(`pillar-${code}`).click();
    await expect(page).toHaveURL(new RegExp(`/home/pillar/${SLUGS[code]}`));
    await expect(page.getByTestId("pillar-detail")).toHaveAttribute("data-pillar", code);
    await page.goBack();
    await expect(page.getByTestId("pillar-grid")).toBeVisible();
  }
  // R-DEC-16: U/S only through the optional five-pillar layout (SCR-03 tabs)
  await page.getByTestId("five-pillar-link").click();
  for (const [code, slug] of Object.entries(SLUGS)) {
    await page.getByTestId(`pillar-tab-${code}`).click();
    await expect(page).toHaveURL(new RegExp(`/home/pillar/${slug}`));
    await expect(page.getByTestId(`pillar-tab-${code}`)).toHaveAttribute("aria-current", "page");
  }
  await page.goto("/home");
  await expect(page.getByTestId("alert-row").first()).toHaveAttribute("data-severity", "critical");
});

test("CFO: Finance drill-down then chat about cash flow", async ({ page }) => {
  await page.route("**/api/backend/ai/chat/stream", (route) =>
    route.fulfill({
      status: 200,
      headers: { "content-type": "text/event-stream" },
      body: [
        `id: 1\nevent: start\ndata: ${JSON.stringify({ conversation_id: "22222222-2222-2222-2222-222222222222", message_id: "m-cf" })}\n\n`,
        `id: 2\nevent: token\ndata: ${JSON.stringify({ delta: "Số dư tiền mặt 20,4 tỷ [1]." })}\n\n`,
        `id: 3\nevent: done\ndata: ${JSON.stringify({ message_id: "m-cf", answer: "Số dư tiền mặt 20,4 tỷ [1].", sources: [{ type: "metric_value", id: "cash", label: "Số dư tiền mặt", value: 20400000000 }], function_calls: [], truncated: false, warnings: [] })}\n\n`,
      ].join(""),
    }),
  );
  await loginAs(page, "cfo@abc.demo");
  await expect(page.getByTestId("pillar-F")).toHaveAttribute("data-status", /ok|warning|critical/);
  await page.getByTestId("pillar-F").click();
  await expect(page).toHaveURL(/\/home\/pillar\/finance/);
  await expect(page.getByTestId("fin-card")).toHaveCount(6);
  await expect(page.getByTestId("fin-card-cash").getByTestId("fin-value")).toHaveText("12,6 tỷ");
  await page.getByTestId("nav-ask").click();
  await page.getByTestId("chat-input").fill("Tình hình cash flow?");
  await page.getByTestId("chat-send").click();
  await expect(page.getByTestId("answer")).toContainText("20,4 tỷ");
});

test("REVIEWER: queue → open → correct → approve → invoice created", async ({ page }) => {
  // Seed fresh so it is not cleaned up by the review-detail.spec.ts afterAll running concurrently.
  const doc = seedReviewDoc();
  await loginAs(page, "reviewer@abc.demo");
  await expect(page).toHaveURL(/\/home$/);
  await page.getByTestId("nav-data").click();
  // M1.5: /data is the Data Inbox (SCR-45) — the review link sits on the document's row
  await expect(page).toHaveURL(/\/data$/);
  await page.locator(`[data-testid="inbox-row"][data-doc="${doc.document_id}"]`).getByTestId("inbox-review").click();
  await expect(page).toHaveURL(new RegExp(`/data/review/${doc.document_id}$`));
  await expect(page.getByTestId("field-row")).toHaveCount(8);
  // FR-DC-16 / R-DEC-69: trường trọng yếu (MST + 3 trường tiền) are confirmed one by one before approve
  for (const name of ["seller_tax_code", "subtotal", "vat_amount", "total_amount"]) {
    await page.locator(`[data-field=${name}]`).getByTestId("field-confirm").check();
  }
  const seller = page.locator("[data-field=seller_name]");
  await seller.getByTestId("field-input").fill("Công ty Văn phòng Phẩm Sài Gòn");
  await seller.getByTestId("field-reason").fill("OCR thiếu dấu");
  await page.getByTestId("approve").click();
  // R-DEC-61: REV has no finance:write → APPROVED; office@ (MGR ADM, finance:write d) commits (EP-DC-23)
  await expect(page.getByRole("status")).toContainText("Đã duyệt — chờ người có quyền ghi (finance:write)");
  await expect(page).toHaveURL(/\/data\/review$/);
  await page.context().clearCookies();
  await login(page, "office@abc.demo");
  await page.goto(`/data/review/${doc.document_id}`);
  await expect(page.getByTestId("approved-state")).toBeVisible();
  await page.getByTestId("commit").click();
  await expect(page.getByTestId("undo-toast")).toBeVisible();
  await page.getByTestId("undo-toast").getByRole("button", { name: "Đóng" }).click();
  // Invoice may land on page 2 of the list (20/page, many E2E invoices) — verify via API instead.
  const r = await page.request.get(`/api/backend/finance/invoices?direction=IN&sort_by=created_at&order=desc&limit=5`);
  expect(r.ok()).toBeTruthy();
  const numbers = ((await r.json()).data as { number: string }[]).map((i) => i.number);
  expect(numbers).toContain(doc.invoice_number);
});

test("HR: dashboard shows O (+ public F headline), employees list", async ({ page }) => {
  await loginAs(page, "hr@abc.demo");
  await expect(page.getByTestId("pillar-O")).toBeVisible();
  // scope_pillars={O}; F stays as the public METRIC-FIN-01 headline (02 §6.1, dashboard.visible_pillars)
  await expect(page.getByTestId("pillar-grid").locator("> [data-testid^=pillar-]")).toHaveCount(2);
  await expect(page.getByTestId("pillar-C")).toHaveCount(0);
  await page.getByTestId("nav-business").click();
  await page.getByTestId("sublink-employees").click();
  await expect(page).toHaveURL(/\/business\/hr\/employees$/);
  await expect(page.getByTestId("employee-row").first()).toBeVisible();
  await expect(page.getByTestId("employee-total")).toContainText(/\d+/);
  await page.getByTestId("employee-search").fill("Phan");
  await expect(page.getByTestId("employee-row").first()).toContainText("Phan");
});

test("ADMIN: audit log page, no business dashboards", async ({ page }) => {
  const password = process.env.DEMO_ADMIN_PASSWORD ?? rootEnv().DEMO_ADMIN_PASSWORD;
  expect(password, "DEMO_ADMIN_PASSWORD must be set in .env").toBeTruthy();
  await loginWithPassword(page, "admin@abc.demo", password ?? "");
  await expect(page).toHaveURL(/\/home$/);
  await page.getByTestId("nav-admin").click();
  await expect(page).toHaveURL(/\/admin$/);
  // SCR-50 admin overview cards → navigate via admin-card-audit (no ComingSoon sublink)
  await page.getByTestId("admin-card-audit").click();
  await expect(page).toHaveURL(/\/admin\/audit$/);
  await expect(page.getByTestId("audit-row").first()).toBeVisible();
  await page.getByTestId("audit-action").fill("auth.login");
  await expect(page.getByTestId("audit-row").first()).toHaveAttribute("data-action", "auth.login");
  await page.goto("/home/pillar/finance");
  await expect(page.getByTestId("forbidden")).toBeVisible();
});

test("MGR: no Executive dashboard, Công việc → Phê duyệt, AI chat open", async ({ page }) => {
  await login(page, "manager@abc.demo");
  await expect(page.getByTestId("coming-soon")).toHaveAttribute("data-scr", "SCR-40");
  await expect(page.getByTestId("pillar-grid")).toHaveCount(0);
  await page.getByTestId("nav-work").click();
  await expect(page).toHaveURL(/\/work$/);
  await expect(page.getByTestId("work-tab-board")).toBeVisible();
  await page.goto("/work/approvals");
  await expect(page.getByTestId("approvals")).toBeVisible();
  await page.getByTestId("nav-ask").click();
  await expect(page.getByTestId("chat-input")).toBeVisible();
});

test("EMP: personal scope — goals tree, work, no approvals, no admin", async ({ page }) => {
  await login(page, "employee@abc.demo");
  await expect(page.getByTestId("pillar-grid")).toHaveCount(0);
  await page.getByTestId("nav-goals").click();
  await expect(page.getByTestId("goals-tree")).toHaveAttribute("data-scr", "SCR-41");
  await expect(page.getByTestId("nav-admin")).toHaveCount(0);
  for (const denied of ["/work/approvals", "/admin", "/business/finance/invoices"]) {
    await page.goto(denied);
    await expect(page.getByTestId("forbidden")).toBeVisible();
  }
});


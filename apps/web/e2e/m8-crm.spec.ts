import type { Browser, Page } from "@playwright/test";
import { expect, test } from "./fixtures";
import { loginSettled } from "./helpers";

/**
 * TC-M8-04 (e2e, real API) — M8: CRM views on the existing sales model (R-DEC-175), CFO OUT
 * invoice by the customer's MST (R-DEC-172), hiring-plan approval through the approval inbox
 * (R-DEC-173), readable role matrix (R-DEC-174). Writes only to the stack under test (isolated).
 */
const uniq = () => `${Date.now().toString(36)}${Math.floor(Math.random() * 1e3)}`.toUpperCase();
const mst = () => `03${String(Date.now()).slice(-8)}`;

async function as(browser: Browser, email: string): Promise<Page> {
  const page = await (await browser.newContext()).newPage();
  await loginSettled(page, email);
  return page;
}

async function createClient(page: Page, name: string, tax?: string) {
  await page.goto("/business/sales/records?tab=clients");
  await page.getByTestId("records-clients-create").click();
  const ed = page.getByTestId("records-clients-editor");
  await ed.getByTestId("records-clients-editor-name").fill(name);
  if (tax) await ed.getByTestId("records-clients-editor-tax_code").fill(tax);
  await ed.getByTestId("records-clients-editor-submit").click();
  await expect(ed).toHaveCount(0);
}

async function createDeal(page: Page, name: string, client: string) {
  await page.goto("/business/sales/records?tab=deals");
  await page.getByTestId("records-deals-create").click();
  const d = page.getByTestId("records-deals-editor");
  await d.getByTestId("records-deals-editor-name").fill(name);
  await d.getByTestId("records-deals-editor-client_id").selectOption({ label: client });
  await d.getByTestId("records-deals-editor-deal_value").fill("500000000");
  await d.getByTestId("records-deals-editor-probability_pct").fill("30");
  await d.getByTestId("records-deals-editor-expected_close_date").fill("2026-12-15");
  await d.getByTestId("records-deals-editor-submit").click();
  await expect(d).toHaveCount(0);
}

test.describe("M8 · CRM, approvals, OUT invoice", () => {
  test("Sales DIR: pipeline board move → deal detail history → Account 360 → lost needs a reason", async ({ browser }) => {
    const tag = uniq();
    const page = await as(browser, "sales@abc.demo");
    await createClient(page, `KH CRM ${tag}`);
    await createDeal(page, `CH CRM ${tag}`, `KH CRM ${tag}`);

    await page.goto("/business/sales/pipeline");
    const card = page.getByTestId("crm-col-lead").getByTestId("crm-card").filter({ hasText: `CH CRM ${tag}` });
    await expect(card).toBeVisible();
    await card.getByTestId("crm-card-move").selectOption("qualified");
    await expect(page.getByTestId("crm-col-qualified").getByTestId("crm-card").filter({ hasText: `CH CRM ${tag}` })).toBeVisible();

    await page.getByTestId("crm-col-qualified").getByRole("link", { name: `CH CRM ${tag}` }).click();
    await expect(page.getByTestId("deal-detail")).toBeVisible();
    await expect(page.getByTestId("deal-stage")).toContainText("Đã sàng lọc");
    await expect(page.getByTestId("deal-history").locator("li")).toHaveCount(2); // lead → qualified

    await page.getByTestId("deal-move").selectOption("closed_lost");
    await expect(page.getByTestId("lost-reason-confirm")).toBeDisabled(); // reason required (BR-011)
    await page.getByTestId("lost-reason-input").fill("Khách chọn đối thủ");
    await page.getByTestId("lost-reason-confirm").click();
    await expect(page.getByTestId("deal-stage")).toContainText("Thua");

    await page.getByTestId("deal-client").click();
    await expect(page.getByTestId("client-detail")).toBeVisible();
    await expect(page.getByTestId("client-deals")).toContainText(`CH CRM ${tag}`);

    await page.goto("/business/sales");
    await expect(page.getByTestId("funnel-row")).toHaveCount(5);
    await expect(page.getByTestId("forecast-expected")).not.toBeEmpty();
    await expect(page.getByTestId("sales-ranking")).toBeVisible();
  });

  test("CFO: OUT invoice linked from the customer's MST; no pipeline / client records", async ({ browser }) => {
    const tag = uniq();
    const tax = mst();
    const sales = await as(browser, "sales@abc.demo");
    await createClient(sales, `KH MST ${tag}`, tax);

    const cfo = await as(browser, "cfo@abc.demo");
    await cfo.goto("/business/finance/records?tab=invoices");
    await cfo.getByTestId("records-invoices-create").click();
    const inv = cfo.getByTestId("records-invoices-editor");
    await inv.getByTestId("records-invoices-editor-direction").selectOption("OUT");
    await inv.getByTestId("records-invoices-editor-number").fill(`OUT${tag}`);
    await inv.getByTestId("records-invoices-editor-issued_on").fill("2026-11-01");
    await inv.getByTestId("records-invoices-editor-due_date").fill("2026-11-30");
    await inv.getByTestId("records-invoices-editor-counterparty_tax_code").fill(tax);
    await inv.getByTestId("line-0-description").fill("Bảo trì máy in");
    await inv.getByTestId("line-0-unit_price").fill("3000000");
    await inv.getByTestId("records-invoices-editor-submit").click();
    await expect(inv).toHaveCount(0);
    await expect(cfo.getByTestId("records-invoices-table").getByTestId("record-row").filter({ hasText: `OUT${tag}` })).toBeVisible();

    await cfo.goto("/business/sales");
    await expect(cfo.getByTestId("sales-funnel")).toBeVisible(); // aggregates (sales:query) stay open
    await expect(cfo.getByTestId("sales-ranking")).toHaveCount(0);
    const res = await cfo.goto("/business/sales/pipeline");
    expect(res?.status()).toBe(403);
  });

  test("Hiring plan: HR-DIR submits → CEO approves in /work/approvals → plan approved", async ({ browser }) => {
    const tag = uniq();
    const hr = await as(browser, "hr@abc.demo");
    await hr.goto("/business/hr/records?tab=hiringPlans");
    await hr.getByTestId("records-hiringPlans-create").click();
    const h = hr.getByTestId("records-hiringPlans-editor");
    await h.getByTestId("records-hiringPlans-editor-position").fill(`Kế toán M8 ${tag}`);
    await h.getByTestId("records-hiringPlans-editor-department_id").selectOption({ index: 1 });
    await h.getByTestId("records-hiringPlans-editor-headcount").fill("1");
    await h.getByTestId("records-hiringPlans-editor-start_date").fill("2026-11-10");
    await h.getByTestId("records-hiringPlans-editor-target_date").fill("2026-12-31");
    await h.getByTestId("records-hiringPlans-editor-submit").click();
    await expect(h).toHaveCount(0);
    const row = hr.getByTestId("records-hiringPlans-table").getByTestId("record-row").filter({ hasText: `Kế toán M8 ${tag}` });
    await row.getByTestId("record-action-submit").click();
    await hr.getByTestId("records-hiringPlans-action-submit").click();
    await expect(row).toContainText("Chờ duyệt");

    const ceo = await as(browser, "ceo@abc.demo");
    await ceo.goto("/work/approvals?kind=hiring_plan");
    const item = ceo.getByTestId("approvals-list").locator("[data-kind=hiring_plan]").filter({ hasText: `Kế toán M8 ${tag}` });
    await item.click();
    await expect(ceo.getByTestId("approval-title")).toContainText(`Kế toán M8 ${tag}`);
    await ceo.getByTestId("approval-approve").click();
    await ceo.getByTestId("approve-dialog-confirm").click(); // approve: reason optional (reject requires one)
    // by design the decision closes the detail panel and confirms with a toast; the request then
    // leaves the pending list (the HR side below checks the plan itself is approved)
    await expect(ceo.getByRole("status").filter({ hasText: /Đã duyệt yêu cầu|approved/i })).toBeVisible();
    await expect(item).toHaveCount(0);

    await hr.reload();
    await expect(hr.getByTestId("records-hiringPlans-table").getByTestId("record-row").filter({ hasText: `Kế toán M8 ${tag}` })).toContainText("Đã duyệt");
  });

  test("Role matrix reads in plain language and links role assignment", async ({ browser }) => {
    const ceo = await as(browser, "ceo@abc.demo");
    await ceo.goto("/admin/roles");
    await expect(ceo.locator("[data-perm='finance:write'] [data-testid=perm-label]")).toHaveText("Tài chính · Tạo / sửa / lưu trữ");
    await expect(ceo.locator("[data-perm='hr:approve'] [data-testid=perm-label]")).toHaveText("Nhân sự · Phê duyệt");
    await expect(ceo.getByTestId("roles-khoi-note")).toBeVisible();
    await expect(ceo.getByTestId("roles-assign-link")).toHaveAttribute("href", "/admin/users");
  });
});

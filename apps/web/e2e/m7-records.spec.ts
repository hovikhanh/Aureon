import type { Page } from "@playwright/test";
import { expect, test } from "./fixtures";
import { loginSettled } from "./helpers";

/**
 * TC-M7-02 (e2e, real API) — business-record CRUD per role over the existing endpoints
 * (EP-FIN-02..07, EP-SAL-01..04, EP-HR-02..10). Writes go to the stack under test only
 * (run with E2E_BASE_URL / E2E_API_URL / DATABASE_URL of an isolated stack). RBAC is the
 * existing matrix: DIR writes inside the khối, CEO writes sales only, REV reads.
 */
const uniq = () => `${Date.now().toString(36)}${Math.floor(Math.random() * 1e3)}`.toUpperCase();

async function openTab(page: Page, domain: string, tab: string) {
  await page.goto(`/business/${domain}/records?tab=${tab}`);
  await expect(page.getByTestId(`records-${tab}`)).toBeVisible();
}
const editor = (page: Page, tab: string) => page.getByTestId(`records-${tab}-editor`);
const row = (page: Page, tab: string, text: string) => page.getByTestId(`records-${tab}-table`).getByTestId("record-row").filter({ hasText: text });

test.describe("M7 · records CRUD", () => {
  test("CFO: revenue create → edit → archive; invoice create → record payment", async ({ page }) => {
    const tag = uniq();
    await loginSettled(page, "cfo@abc.demo");
    await openTab(page, "finance", "revenues");
    await page.getByTestId("records-revenues-create").click();
    const ed = editor(page, "revenues");
    await ed.getByTestId("records-revenues-editor-amount").fill("125000000");
    await ed.getByTestId("records-revenues-editor-category").selectOption("service");
    await ed.getByTestId("records-revenues-editor-recognized_on").fill("2026-11-02");
    await ed.getByTestId("records-revenues-editor-description").fill(`E2E doanh thu ${tag}`);
    await ed.getByTestId("records-revenues-editor-submit").click();
    await expect(ed).toHaveCount(0);
    const r = row(page, "revenues", `E2E doanh thu ${tag}`);
    await expect(r).toBeVisible();

    await r.getByTestId("record-edit").click();
    await editor(page, "revenues").getByTestId("records-revenues-editor-amount").fill("130000000");
    await editor(page, "revenues").getByTestId("records-revenues-editor-submit").click();
    await expect(r).toContainText("130.000.000");

    await r.getByTestId("record-archive").click();
    await page.getByTestId("record-archive-confirm").click();
    await expect(row(page, "revenues", `E2E doanh thu ${tag}`)).toHaveCount(0);

    await openTab(page, "finance", "invoices");
    await page.getByTestId("records-invoices-create").click();
    const inv = editor(page, "invoices");
    // CFO cannot read sales clients (khối C) → an IN (purchase) invoice with a counterparty
    await inv.getByTestId("records-invoices-editor-direction").selectOption("IN");
    await expect(inv.getByTestId("records-invoices-editor-client_id")).toHaveCount(0);
    await inv.getByTestId("records-invoices-editor-number").fill(`E2E${tag}`);
    await inv.getByTestId("records-invoices-editor-issued_on").fill("2026-11-01");
    await inv.getByTestId("records-invoices-editor-due_date").fill("2026-11-30");
    await inv.getByTestId("records-invoices-editor-counterparty_name").fill("Công ty E2E");
    await inv.getByTestId("records-invoices-editor-status").selectOption("sent");
    await inv.getByTestId("line-0-description").fill("Máy in laser");
    await inv.getByTestId("line-0-quantity").fill("2");
    await inv.getByTestId("line-0-unit_price").fill("5000000");
    await inv.getByTestId("records-invoices-editor-submit").click();
    await expect(inv).toHaveCount(0);
    const ir = row(page, "invoices", `E2E${tag}`);
    await expect(ir).toContainText("11.000.000"); // 2 × 5 tr + VAT 10 %
    await ir.getByTestId("record-action-pay").click();
    const pay = page.getByTestId("records-invoices-action");
    await pay.getByTestId("records-invoices-action-amount_paid").fill("11000000");
    await pay.getByTestId("records-invoices-action-paid_at").fill("2026-11-03");
    await pay.getByTestId("records-invoices-action-submit").click();
    await expect(ir.getByTestId("record-action-pay")).toHaveCount(0); // paid → no more payment
  });

  test("Sales DIR: client → deal (owner = me) → change stage; finance records are the 403 page", async ({ page }) => {
    const tag = uniq();
    await loginSettled(page, "sales@abc.demo");
    await openTab(page, "sales", "clients");
    await page.getByTestId("records-clients-create").click();
    const c = editor(page, "clients");
    await c.getByTestId("records-clients-editor-name").fill(`Khách E2E ${tag}`);
    await c.getByTestId("records-clients-editor-status").selectOption("prospect");
    await c.getByTestId("records-clients-editor-submit").click();
    await expect(c).toHaveCount(0);

    await openTab(page, "sales", "deals");
    await page.getByTestId("records-deals-create").click();
    const d = editor(page, "deals");
    await d.getByTestId("records-deals-editor-name").fill(`Deal E2E ${tag}`);
    await d.getByTestId("records-deals-editor-client_id").selectOption({ label: `Khách E2E ${tag}` });
    await d.getByTestId("records-deals-editor-deal_value").fill("300000000");
    await d.getByTestId("records-deals-editor-probability_pct").fill("40");
    await d.getByTestId("records-deals-editor-expected_close_date").fill("2026-12-20");
    await expect(d.getByTestId("records-deals-editor-owner_id")).not.toHaveValue(""); // defaults to me
    await d.getByTestId("records-deals-editor-submit").click();
    await expect(d).toHaveCount(0);
    const dr = row(page, "deals", `Deal E2E ${tag}`);
    await dr.getByTestId("record-action-stage").click();
    const st = page.getByTestId("records-deals-action");
    await st.getByTestId("records-deals-action-to_stage").selectOption("negotiation");
    await st.getByTestId("records-deals-action-submit").click();
    await expect(dr).toContainText("Đàm phán");

    const res = await page.goto("/business/finance/records");
    expect(res?.status()).toBe(403);
    await expect(page.getByTestId("forbidden")).toBeVisible();
  });

  test("HR DIR: employee create → edit; hiring plan create → submit (approve offered to HR-DIR, R-DEC-173)", async ({ page }) => {
    const tag = uniq();
    await loginSettled(page, "hr@abc.demo");
    await openTab(page, "hr", "employees");
    await page.getByTestId("records-employees-create").click();
    const e = editor(page, "employees");
    await e.getByTestId("records-employees-editor-employee_code").fill(`E2E${tag}`.slice(0, 20));
    await e.getByTestId("records-employees-editor-full_name").fill(`Nguyễn E2E ${tag}`);
    await e.getByTestId("records-employees-editor-department_id").selectOption({ index: 1 });
    await e.getByTestId("records-employees-editor-hire_date").fill("2026-11-01");
    await e.getByTestId("records-employees-editor-status").selectOption("probation");
    await e.getByTestId("records-employees-editor-submit").click();
    await expect(e).toHaveCount(0);
    await page.getByTestId("records-employees-search").fill(`E2E ${tag}`);
    const er = row(page, "employees", `Nguyễn E2E ${tag}`);
    await expect(er).toBeVisible();
    await er.getByTestId("record-edit").click();
    await editor(page, "employees").getByTestId("records-employees-editor-title").fill("Chuyên viên E2E");
    await editor(page, "employees").getByTestId("records-employees-editor-submit").click();
    await expect(er).toContainText("Chuyên viên E2E");

    await openTab(page, "hr", "hiringPlans");
    await page.getByTestId("records-hiringPlans-create").click();
    const h = editor(page, "hiringPlans");
    await h.getByTestId("records-hiringPlans-editor-position").fill(`Kế toán E2E ${tag}`);
    await h.getByTestId("records-hiringPlans-editor-department_id").selectOption({ index: 1 });
    await h.getByTestId("records-hiringPlans-editor-headcount").fill("2");
    await h.getByTestId("records-hiringPlans-editor-start_date").fill("2026-11-10");
    await h.getByTestId("records-hiringPlans-editor-target_date").fill("2026-12-31");
    await h.getByTestId("records-hiringPlans-editor-submit").click();
    await expect(h).toHaveCount(0);
    const hr = row(page, "hiringPlans", `Kế toán E2E ${tag}`);
    await hr.getByTestId("record-action-submit").click();
    await page.getByTestId("records-hiringPlans-action-submit").click();
    await expect(hr).toContainText("Chờ duyệt");
    // R-DEC-173: HR-DIR (khối O) or the CEO decides — the button is offered; the decision itself
    // (by another HR director or the CEO in /work/approvals) is covered by m8-crm.spec
    await expect(hr.getByTestId("record-action-approve")).toHaveCount(1);
  });

  test("CEO: finance + HR read only (no write permission), sales writable", async ({ page }) => {
    await loginSettled(page, "ceo@abc.demo");
    for (const [domain, tab] of [["finance", "revenues"], ["hr", "employees"]] as const) {
      await openTab(page, domain, tab);
      await expect(page.getByTestId("records-readonly")).toBeVisible();
      await expect(page.getByTestId(`records-${tab}-create`)).toHaveCount(0);
      await expect(page.getByTestId("record-edit")).toHaveCount(0);
    }
    await openTab(page, "sales", "clients");
    await expect(page.getByTestId("records-clients-create")).toBeVisible();
  });

  test("Reviewer: no general finance records (D-07, R-DEC-183)", async ({ page }) => {
    // REV `finance:read ◑r` reads finance only inside an assigned review: the records editor is
    // not offered and the route answers 403
    await loginSettled(page, "reviewer@abc.demo");
    await expect(page.getByTestId("nav-business")).toHaveCount(0);
    await page.goto("/business/finance/records?tab=invoices");
    await expect(page.getByTestId("forbidden")).toBeVisible();
  });
});

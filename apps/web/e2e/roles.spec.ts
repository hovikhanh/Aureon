import { expect, test } from "@playwright/test";
import { loginAs, loginWithPassword } from "./helpers";
import { cleanupReviewDocs, rootEnv, seedReviewDoc } from "./support/seed";

/** T-516 — full regression across the 5 demo roles (CEO, CFO, REVIEWER, HR, ADMIN). */
test.afterAll(() => cleanupReviewDocs());

const SLUGS = { F: "finance", O: "operations", C: "customer", U: "product", S: "strategy" } as const;

test("CEO: 5 pillar cards each drill down, 13 alerts", async ({ page }) => {
  await loginAs(page, "ceo@abc.demo");
  await expect(page.getByTestId("alert-row")).toHaveCount(13);
  for (const [code, slug] of Object.entries(SLUGS)) {
    await expect(page.getByTestId(`pillar-${code}`)).toHaveAttribute("data-status", /ok|warning|critical/);
    await page.getByTestId(`pillar-${code}`).click();
    await expect(page).toHaveURL(new RegExp(`/home/pillar/${slug}`));
    await expect(page.getByTestId("pillar-detail")).toHaveAttribute("data-pillar", code);
    await page.goBack();
    await expect(page.getByTestId("pillar-grid")).toBeVisible();
  }
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
  const doc = seedReviewDoc();
  await loginAs(page, "reviewer@abc.demo");
  await expect(page).toHaveURL(/\/home$/);
  await page.getByTestId("nav-data").click();
  await page.getByTestId("sublink-review").click();
  await expect(page).toHaveURL(/\/data\/review$/);
  await page.locator(`[data-document-id="${doc.document_id}"]`).getByTestId("review-link").click();
  await expect(page.getByTestId("field-row")).toHaveCount(8);
  const seller = page.locator("[data-field=seller_name]");
  await seller.getByTestId("field-input").fill("Công ty Văn phòng Phẩm Sài Gòn");
  await seller.getByTestId("field-reason").fill("OCR thiếu dấu");
  await page.getByTestId("approve").click();
  await expect(page.getByRole("status")).toContainText("Đã ghi vào Finance");
  await page.goto("/business/finance/invoices");
  await page.getByTestId("dir-IN").click();
  await expect(page.locator(`[data-testid=invoice-row][data-number="${doc.invoice_number}"]`)).toBeVisible();
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
  await page.getByTestId("sublink-audit").click();
  await expect(page).toHaveURL(/\/admin\/audit$/);
  await expect(page.getByTestId("audit-row").first()).toBeVisible();
  await page.getByTestId("audit-action").fill("auth.login");
  await expect(page.getByTestId("audit-row").first()).toHaveAttribute("data-action", "auth.login");
  await page.goto("/home/pillar/finance");
  await expect(page.getByTestId("forbidden")).toBeVisible();
});

import { expect, test } from "./fixtures";
import { loginAs } from "./helpers";
import { cleanupReviewDocs, seedReviewDoc } from "./support/seed";

test.afterAll(() => cleanupReviewDocs());

test.describe("SCR-18a review queue (T-507)", () => {
  test("lists seeded document with filters", async ({ page }) => {
    const doc = seedReviewDoc();
    await loginAs(page, "reviewer@abc.demo");
    await page.goto("/data/review");
    const row = page.locator(`[data-testid=queue-row][data-document-id="${doc.document_id}"]`);
    await expect(row).toBeVisible();
    await expect(row).toContainText(doc.invoice_number);
    await expect(row).toContainText("Hóa đơn");
    await expect(row.getByTestId("confidence-badge")).toBeVisible();

    await page.getByLabel("Loại tài liệu").selectOption("CONTRACT");
    await expect(row).toHaveCount(0);
    await page.getByLabel("Loại tài liệu").selectOption("INVOICE");
    await expect(row).toBeVisible();
    await page.getByLabel("Trạng thái").selectOption("NEEDS_REVIEW");
    await expect(row).toBeVisible();

    await row.getByTestId("review-link").click();
    await expect(page).toHaveURL(new RegExp(`/data/review/${doc.document_id}$`));
  });

  test("empty state with upload button", async ({ page }) => {
    await page.route("**/api/backend/idp/review-queue**", (r) =>
      r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ data: [], meta: { pagination: { total: 0, limit: 20, offset: 0, has_next: false } } }) }),
    );
    await loginAs(page, "reviewer@abc.demo");
    await page.goto("/data/review");
    await expect(page.getByTestId("queue-empty")).toContainText("Không có tài liệu cần review");
    await expect(page.getByTestId("queue-empty").getByTestId("upload-button")).toBeVisible();
  });
});

import { expect, test } from "./fixtures";
import { loginAs } from "./helpers";
import { cleanupReviewDocs, seedReviewDoc } from "./support/seed";

test.afterAll(() => cleanupReviewDocs());

test.describe("SCR-18b review detail (T-508)", () => {
  test("8 fields, correct one, approve → invoice visible in Finance", async ({ page }) => {
    const doc = seedReviewDoc();
    await loginAs(page, "reviewer@abc.demo");
    await page.goto(`/data/review/${doc.document_id}`);
    const rows = page.getByTestId("field-row");
    await expect(rows).toHaveCount(8);
    await expect(page.locator("[data-testid=field-row] >> text=Trọng yếu")).toHaveCount(3);
    await expect(page.locator('[data-field=seller_name] [data-testid=confidence-badge]')).toHaveAttribute("data-band", "MEDIUM");

    // hover highlights the source line
    await page.locator("[data-field=invoice_number]").hover();
    await expect(page.locator('[data-testid=source-page] [data-highlight=true]')).toContainText(doc.invoice_number);

    // money correction without reason → red border + message, approve blocked
    const vat = page.locator("[data-field=vat_amount]");
    await vat.getByTestId("field-input").fill("1000001");
    await page.getByTestId("approve").click();
    await expect(vat.getByTestId("field-input")).toHaveAttribute("aria-invalid", "true");
    await expect(vat).toContainText("Trường tiền cần ghi lý do sửa");
    await vat.getByTestId("field-input").fill("1000000");

    // correct one non-money field
    const seller = page.locator("[data-field=seller_name]");
    await seller.getByTestId("field-input").fill("Công ty Văn phòng Phẩm Sài Gòn");
    await seller.getByTestId("field-reason").fill("OCR thiếu dấu");
    await page.getByTestId("approve").click();

    // M1.5: a committing approve shows the UndoToast (06 §5.1) before returning to the queue
    await expect(page.getByTestId("undo-toast")).toBeVisible();
    await page.getByTestId("undo-toast").getByRole("button", { name: "Đóng" }).click();
    await expect(page).toHaveURL(/\/data\/review$/);
    await expect(page.locator(`[data-document-id="${doc.document_id}"]`)).toHaveCount(0);

    // Invoice may be on page 2+ of the list (20/page, many E2E invoices) — verify via API.
    const r = await page.request.get(`/api/backend/finance/invoices?direction=IN&sort_by=created_at&order=desc&limit=5`);
    expect(r.ok()).toBeTruthy();
    const numbers = ((await r.json()).data as { number: string }[]).map((i) => i.number);
    expect(numbers).toContain(doc.invoice_number);
  });

  test("reject requires a reason", async ({ page }) => {
    const doc = seedReviewDoc();
    await loginAs(page, "reviewer@abc.demo");
    await page.goto(`/data/review/${doc.document_id}`);
    await page.getByTestId("reject").click();
    await page.getByTestId("reject-confirm").click();
    await expect(page.getByTestId("reject-dialog")).toContainText("Vui lòng nhập lý do");
    await page.getByTestId("reject-reason").fill("Ảnh mờ, không đọc được");
    await page.getByTestId("reject-confirm").click();
    await expect(page).toHaveURL(/\/data\/review$/);
    await expect(page.getByRole("status")).toContainText("Đã từ chối tài liệu");
  });
});

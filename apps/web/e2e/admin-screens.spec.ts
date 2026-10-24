import { expect, test } from "./fixtures";
import { login } from "./helpers";

/**
 * T-617F / TC-M12-18 — M1.2 admin screens on the mock BFF (API_MODE=mock): SCR-50 cards per
 * role, SCR-51 tree + `as_of` past = read only + transfer history, create department, SCR-52
 * positions, SCR-53 lock with reason + self-lock disabled, SCR-54 matrix, SCR-14 filters, the
 * Header bell (badge, read-all) and Sidebar default deny. `@mock-only`: the mock store is
 * deterministic; the real-stack flow is T-618 (`admin-org.spec.ts`).
 */
test.describe("M1.2 admin screens (TC-M12-18)", { tag: ["@mock", "@mock-only"] }, () => {
  test("ADM: overview cards, org tree as_of, create department, positions", async ({ page }) => {
    await login(page, "admin@abc.demo");
    await page.getByTestId("nav-admin").click();
    await expect(page).toHaveURL(/\/admin$/);
    for (const k of ["org", "positions", "users", "roles", "audit"]) await expect(page.getByTestId(`admin-card-${k}`)).toBeVisible();

    await page.getByTestId("admin-card-org").click();
    await expect(page.getByTestId("org-tree")).toBeVisible();
    // past date → read-only banner, NV-0049 still in Sales (seeded transfer 2024-01-01)
    await page.getByTestId("org-as-of").fill("2023-06-01");
    await expect(page.getByTestId("org-past-banner")).toContainText("01/06/2023");
    await expect(page.getByTestId("org-new-dept")).toHaveCount(0);
    await page.getByTestId("org-node-SAL").click();
    await expect(page.getByTestId("dept-members")).toContainText("NV-0049");
    await page.getByTestId("org-as-of-today").click();
    await page.getByTestId("org-node-SVC").click();
    await page.getByTestId("dept-members").getByText("NV-0049").click();
    await expect(page.getByTestId("emp-history-row")).toHaveCount(2);

    await page.getByTestId("org-new-dept").click();
    await page.getByTestId("dept-code").fill("QA");
    await page.getByTestId("dept-name").fill("Phòng Chất lượng");
    await page.getByTestId("dept-form-submit").click();
    await expect(page.getByTestId("org-node-QA")).toBeVisible();
    // archive an occupied department → blocked with the reason
    await page.getByTestId("org-node-SVC").click();
    await page.getByTestId("dept-archive").click();
    await page.getByTestId("archive-dept-confirm").click();
    await expect(page.getByTestId("archive-dept-error")).toContainText(/phân công|assignments/);
    await page.keyboard.press("Escape");

    await page.goto("/admin/positions");
    await page.getByTestId("position-new").click();
    await page.getByTestId("position-dept").selectOption({ label: "QA — Phòng Chất lượng" });
    await page.getByTestId("position-code").fill("QA-LEAD");
    await page.getByTestId("position-title").fill("Trưởng nhóm QA");
    await page.getByTestId("position-budget").fill("2");
    await page.getByTestId("position-form-submit").click();
    await expect(page.getByTestId("position-row").filter({ hasText: "QA-LEAD" }).getByTestId("position-vacant")).toHaveText("2");
  });

  test("ADM: users lock with reason, no self-lock, roles matrix, audit filter, bell", async ({ page }) => {
    await login(page, "admin@abc.demo");
    await page.goto("/admin/users");
    await expect(page.getByTestId("user-row").filter({ hasText: "admin@abc.demo" }).getByTestId("user-lock")).toBeDisabled();
    const row = page.getByTestId("user-row").filter({ hasText: "employee@abc.demo" });
    await row.getByTestId("user-lock").click();
    await page.getByTestId("user-lock-dialog-confirm").click();
    await expect(page.getByTestId("user-lock-dialog-error")).toBeVisible(); // reason required
    await page.getByTestId("user-lock-dialog-reason").fill("Nghỉ dài hạn");
    await page.getByTestId("user-lock-dialog-confirm").click();
    await expect(page.getByText(/phiên đăng nhập của người này đã bị thu hồi/)).toBeVisible();
    await expect(row).toHaveAttribute("data-active", "false");

    await page.goto("/admin/roles");
    await expect(page.getByTestId("role-col")).toHaveCount(7);
    await expect(page.locator('[data-perm="hr:admin"] [data-has="true"]')).toHaveCount(3);

    await page.goto("/admin/audit");
    await page.getByTestId("audit-actor-type").selectOption("USER");
    await expect(page.getByTestId("audit-row").first()).toHaveAttribute("data-action", "auth.user_deactivate");
    await page.getByTestId("audit-from").fill("2026-10-10");
    await page.getByTestId("audit-to").fill("2026-10-01");
    await expect(page.getByTestId("audit-range-error")).toBeVisible();

    await expect(page.getByTestId("notification-badge")).toHaveText("3");
    await page.getByTestId("notification-bell").click();
    await expect(page.getByTestId("notification-item")).toHaveCount(3);
    await page.getByTestId("notification-read-all").click();
    await expect(page.getByTestId("notification-badge")).toHaveCount(0);
    await expect(page.getByTestId("notification-bell")).toHaveAttribute("aria-label", /^(Thông báo|Notifications)$/);
  });

  test("CEO: users read only; DIR khối O sees org only; MGR/EMP denied", async ({ page }) => {
    await login(page, "ceo@abc.demo");
    await page.goto("/admin/users");
    await expect(page.getByTestId("users-table")).toBeVisible();
    await expect(page.getByTestId("user-lock")).toHaveCount(0);
    await page.getByTestId("avatar").click();
    await page.getByTestId("logout").click();
    await expect(page).toHaveURL(/\/login/);

    await login(page, "hr@abc.demo");
    await expect(page.getByTestId("nav-admin")).toBeVisible();
    await page.goto("/admin");
    await expect(page.getByTestId("admin-cards").locator("a")).toHaveCount(2);
    await page.goto("/admin/users");
    await expect(page.getByTestId("forbidden")).toBeVisible();
    await page.goto("/admin/org");
    await expect(page.getByTestId("org-new-dept")).toBeVisible();
    await page.getByTestId("avatar").click();
    await page.getByTestId("logout").click();
    await expect(page).toHaveURL(/\/login/);

    await login(page, "cfo@abc.demo");
    await expect(page.getByTestId("nav-admin")).toHaveCount(0);
    await page.goto("/admin/org");
    await expect(page.getByTestId("forbidden")).toBeVisible();
    await page.goto("/home");
    await page.getByTestId("avatar").click();
    await page.getByTestId("logout").click();
    await expect(page).toHaveURL(/\/login/);

    await login(page, "employee@abc.demo");
    await page.goto("/admin/org");
    await expect(page.getByTestId("forbidden")).toBeVisible();
    await page.goto("/home");
    await expect(page.getByTestId("notification-bell")).toBeVisible();
  });
});

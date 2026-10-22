import { expect, test } from "@playwright/test";
import { loginAs } from "./helpers";

test.describe("SCR-13 login (T-502/T-503)", () => {
  test("protected route redirects to /login", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/\/login\?callbackUrl=%2Fdashboard/);
  });

  test("wrong password is rejected with API error", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("Email").fill("ceo@abc.demo");
    await page.getByLabel("Mật khẩu").fill("wrong-password");
    await page.getByRole("button", { name: "Đăng nhập" }).click();
    await expect(page.getByTestId("login-error")).toContainText("Email hoặc mật khẩu không đúng");
    await expect(page).toHaveURL(/\/login/);
  });

  for (const [email, landing] of [
    ["ceo@abc.demo", "/dashboard"],
    ["cfo@abc.demo", "/dashboard"],
    ["reviewer@abc.demo", "/idp/review"],
  ] as const) {
    test(`demo ${email} lands on ${landing}`, async ({ page }) => {
      await loginAs(page, email);
      await expect(page).toHaveURL(new RegExp(`${landing}$`));
    });
  }

  test("role-based nav + 403 on unauthorized route", async ({ page }) => {
    await loginAs(page, "reviewer@abc.demo");
    await expect(page.getByTestId("nav-idp")).toBeVisible();
    await expect(page.getByTestId("nav-dashboard")).toHaveCount(0);
    await page.goto("/dashboard");
    await expect(page.getByTestId("forbidden")).toBeVisible();
  });

  test("logout returns to login", async ({ page }) => {
    await loginAs(page, "ceo@abc.demo");
    await page.getByTestId("avatar").click();
    await page.getByTestId("logout").click();
    await expect(page).toHaveURL(/\/login/);
  });
});

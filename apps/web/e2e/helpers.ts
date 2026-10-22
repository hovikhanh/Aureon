import { expect, type Page } from "@playwright/test";

/** Demo quick-login (DEMO_MODE): pick the account; the password is resolved server-side. */
export async function loginAs(page: Page, email: string): Promise<void> {
  await page.goto("/login");
  await page.getByTestId("demo-select").selectOption(email);
  await expect(page.getByLabel("Email")).toHaveValue(email);
  await page.getByRole("button", { name: /Đăng nhập|Sign in/ }).click();
  await page.waitForURL((u) => !u.pathname.startsWith("/login"));
}

/** Typed credential login (accounts outside the 5-entry demo dropdown, e.g. ADMIN). */
export async function loginWithPassword(page: Page, email: string, password: string): Promise<void> {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel(/Mật khẩu|Password/).fill(password);
  await page.getByRole("button", { name: /Đăng nhập|Sign in/ }).click();
  await page.waitForURL((u) => !u.pathname.startsWith("/login"));
}

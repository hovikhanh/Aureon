import { expect, test, type Page } from "@playwright/test";
import { MOCK_LOGIN_PASSWORD } from "./support/mock";

/**
 * Login helpers (T-606). `login()` is the single entry point: it picks the strategy from the
 * running Playwright project —
 *  - `mock`: typed credentials with the mock-only password (all 10 demo accounts, no backend);
 *  - `real`: demo quick-login (DEMO_MODE, password resolved server-side) for accounts in the
 *    demo dropdown, otherwise typed credentials with `password`.
 */
export function isMockProject(): boolean {
  return test.info().project.name === "mock";
}

async function submit(page: Page): Promise<void> {
  await page.getByRole("button", { name: /Đăng nhập|Sign in/ }).click();
  await page.waitForURL((u) => !u.pathname.startsWith("/login"));
}

/** Demo quick-login (DEMO_MODE): pick the account; the password is resolved server-side. */
export async function loginAs(page: Page, email: string): Promise<void> {
  if (isMockProject()) return loginWithPassword(page, email, MOCK_LOGIN_PASSWORD);
  await page.goto("/login");
  await page.getByTestId("demo-select").selectOption(email);
  await expect(page.getByLabel("Email")).toHaveValue(email);
  await submit(page);
}

/** Typed credential login (accounts outside the demo dropdown, e.g. ADMIN). */
export async function loginWithPassword(page: Page, email: string, password: string): Promise<void> {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel(/Mật khẩu|Password/).fill(isMockProject() ? MOCK_LOGIN_PASSWORD : password);
  await submit(page);
}

/** Project-aware login: `password` is only used on `real` for accounts outside the demo list. */
export async function login(page: Page, email: string, password?: string): Promise<void> {
  if (password === undefined) return loginAs(page, email);
  return loginWithPassword(page, email, password);
}

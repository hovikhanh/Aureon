import { test, type Page } from "@playwright/test";
import { DEMO_ACCOUNTS, demoTestId } from "../src/lib/demo-accounts";
import { MOCK_LOGIN_PASSWORD } from "./support/mock";
import { rootEnv } from "./support/seed";

/** Dev password variables per demo account, in the alias order `core/config.py` reads them. */
const PASSWORD_ENV: Record<string, readonly string[]> = {
  "ceo@abc.demo": ["DEMO_CEO_PASSWORD"],
  "cfo@abc.demo": ["DEMO_CFO_PASSWORD"],
  "sales@abc.demo": ["DEMO_VP_SALES_PASSWORD", "DEMO_SALES_PASSWORD"],
  "hr@abc.demo": ["DEMO_HR_MANAGER_PASSWORD", "DEMO_HR_PASSWORD"],
  "cpo@abc.demo": ["DEMO_CPO_PASSWORD", "DEMO_RISK_MANAGER_PASSWORD"],
  "manager@abc.demo": ["DEMO_MANAGER_PASSWORD"],
  "office@abc.demo": ["DEMO_OFFICE_MANAGER_PASSWORD", "DEMO_MANAGER_PASSWORD"],
  "employee@abc.demo": ["DEMO_EMPLOYEE_PASSWORD"],
  "reviewer@abc.demo": ["DEMO_REVIEWER_PASSWORD"],
  "admin@abc.demo": ["DEMO_ADMIN_PASSWORD"],
};

/** Dev password from the environment / root `.env` (never hard-coded; DEMO_PASSWORD fallback). */
export function devPassword(email: string): string {
  const env = { ...rootEnv(), ...process.env };
  for (const name of PASSWORD_ENV[email] ?? []) if (env[name]) return env[name];
  return env.DEMO_PASSWORD || "";
}

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

/** Demo quick-login (DEMO_MODE): one click per account; the password is resolved server-side. */
export async function loginAs(page: Page, email: string): Promise<void> {
  if (isMockProject()) return loginWithPassword(page, email, MOCK_LOGIN_PASSWORD);
  await page.goto("/login");
  await page.getByTestId(demoTestId(email)).click();
  await page.waitForURL((u) => !u.pathname.startsWith("/login"));
}

/** Typed credential login (accounts outside the demo dropdown, e.g. ADMIN). */
export async function loginWithPassword(page: Page, email: string, password: string): Promise<void> {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel(/Mật khẩu|Password/).fill(isMockProject() ? MOCK_LOGIN_PASSWORD : password);
  await submit(page);
}

/**
 * Project-aware login for any of the 10 demo accounts: demo quick-login when the account is in
 * the dropdown, otherwise typed credentials (explicit `password`, else the dev password).
 */
export async function login(page: Page, email: string, password?: string): Promise<void> {
  const inDropdown = DEMO_ACCOUNTS.some((a) => a.email === email);
  if (password === undefined && inDropdown) return loginAs(page, email);
  return loginWithPassword(page, email, password ?? devPassword(email));
}

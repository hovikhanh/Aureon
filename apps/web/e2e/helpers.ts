import { expect, test, type Page } from "@playwright/test";
import { DEMO_ACCOUNTS } from "../src/lib/demo-accounts";
import { waitForHydration } from "./fixtures";
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
 *  - `real`: pick the account in the SCR-13 demo dropdown (DEMO_MODE + DEMO_LOGIN_AUTOFILL fill
 *    e-mail AND password, R-DEC-28), otherwise typed credentials with `password`.
 */
export function isMockProject(): boolean {
  return test.info().project.name === "mock";
}

async function submit(page: Page): Promise<void> {
  await page.getByRole("button", { name: /Đăng nhập|Sign in/ }).click();
  await page.waitForURL((u) => !u.pathname.startsWith("/login"));
  await waitForHydration(page); // full load via window.location.assign — not through page.goto
}

/** SCR-13 demo dropdown (T-610c): pick → both fields are filled with real values → submit. */
export async function pickDemoAccount(page: Page, email: string): Promise<void> {
  await page.getByLabel(/Tài khoản demo|Demo accounts/).selectOption(email);
  await expect(page.getByLabel("Email")).toHaveValue(email);
  await expect(page.getByLabel(/^(Mật khẩu|Password)$/)).not.toHaveValue("");
}

export async function loginAs(page: Page, email: string): Promise<void> {
  if (isMockProject()) return loginWithPassword(page, email, MOCK_LOGIN_PASSWORD);
  await page.goto("/login");
  await pickDemoAccount(page, email);
  await submit(page);
}

/** Typed credential login (accounts outside the demo dropdown, e.g. ADMIN). */
export async function loginWithPassword(page: Page, email: string, password: string): Promise<void> {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel(/^(Mật khẩu|Password)$/).fill(isMockProject() ? MOCK_LOGIN_PASSWORD : password);
  await submit(page);
}

/**
 * Project-aware login for any of the 10 demo accounts: demo dropdown when the account is in
 * the dropdown, otherwise typed credentials (explicit `password`, else the dev password).
 */
export async function login(page: Page, email: string, password?: string): Promise<void> {
  const inDropdown = DEMO_ACCOUNTS.some((a) => a.email === email);
  if (password === undefined && inDropdown) return loginAs(page, email);
  return loginWithPassword(page, email, password ?? devPassword(email));
}

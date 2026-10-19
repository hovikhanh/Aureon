import type { Page } from "@playwright/test";

/**
 * Demo accounts (08 §2). Passwords come ONLY from env (`DEMO_*_PASSWORD`), never
 * hard-coded (CLAUDE.md § credentials). playwright.config.ts auto-loads the repo-root
 * `.env` into process.env, so `pnpm test:e2e` is reproducible with no manual sourcing.
 */
export const DEMO_ACCOUNTS = {
  "ROLE-01": { email: "ceo@abc.demo", envKey: "DEMO_CEO_PASSWORD", home: "/dashboard" },
  "ROLE-02": { email: "cfo@abc.demo", envKey: "DEMO_CFO_PASSWORD", home: "/dashboard" },
  "ROLE-03": { email: "sales@abc.demo", envKey: "DEMO_SALES_PASSWORD", home: "/dashboard" },
  "ROLE-04": { email: "hr@abc.demo", envKey: "DEMO_HR_PASSWORD", home: "/dashboard" },
  "ROLE-05": { email: "reviewer@abc.demo", envKey: "DEMO_REVIEWER_PASSWORD", home: "/inbox" },
} as const;

export type RoleCode = keyof typeof DEMO_ACCOUNTS;

export function passwordFor(role: RoleCode): string {
  const { envKey } = DEMO_ACCOUNTS[role];
  const pw = process.env[envKey];
  if (!pw) {
    throw new Error(
      `Missing env ${envKey}. Load demo passwords before running E2E: ` +
        `set -a; source .env; set +a; pnpm test:e2e`,
    );
  }
  return pw;
}

/**
 * Log in via the real SCR-13 form. The quick-login buttons now use the real demo passwords
 * (NEXT_PUBLIC_DEMO_PASSWORD_*), but these tests still drive the form directly to assert the
 * form path. After landing on the home route we wait for the app to settle (network idle +
 * the first heading) so later interactions don't race with Next hydration / the RouteGuard
 * session check.
 */
export async function login(page: Page, role: RoleCode): Promise<void> {
  const acc = DEMO_ACCOUNTS[role];
  await page.goto("/login");
  await page.locator("#email").fill(acc.email);
  await page.locator("#password").fill(passwordFor(role));
  await page.getByRole("button", { name: /Đăng nhập/i }).first().click();
  // Auth-context navigates to the role's home route on success.
  await page.waitForURL(`**${acc.home}`, { timeout: 15_000 });
  // Wait until the protected view is actually rendered (past the RouteGuard "checking session"
  // state) and the page is hydrated before the test interacts with it.
  await page.getByRole("heading").first().waitFor({ state: "visible", timeout: 15_000 });
  await page.waitForLoadState("networkidle").catch(() => undefined);
}

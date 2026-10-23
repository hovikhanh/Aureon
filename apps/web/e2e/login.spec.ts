import { expect, test } from "@playwright/test";
import { login, loginAs } from "./helpers";

test.describe("SCR-13 login (T-502/T-503)", () => {
  test("protected route redirects to /login", { tag: "@mock" }, async ({ page }) => {
    await page.goto("/home");
    await expect(page).toHaveURL(/\/login\?callbackUrl=%2Fhome/);
  });

  test("wrong password is rejected with API error", { tag: "@mock" }, async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("Email").fill("ceo@abc.demo");
    await page.getByLabel("Mật khẩu").fill("wrong-password");
    await page.getByRole("button", { name: "Đăng nhập" }).click();
    await expect(page.getByTestId("login-error")).toContainText("Email hoặc mật khẩu không đúng");
    await expect(page).toHaveURL(/\/login/);
  });

  for (const [email, landing] of [
    ["ceo@abc.demo", "/home"],
    ["cfo@abc.demo", "/home"],
    ["reviewer@abc.demo", "/home"],
  ] as const) {
    test(`demo ${email} lands on ${landing}`, async ({ page }) => {
      await loginAs(page, email);
      await expect(page).toHaveURL(new RegExp(`${landing}$`));
    });
  }

  test("role-based nav + 403 on unauthorized route", async ({ page }) => {
    await loginAs(page, "reviewer@abc.demo");
    await expect(page.getByTestId("nav-data")).toBeVisible();
    await expect(page.getByTestId("nav-goals")).toHaveCount(0);
    await page.goto("/home/pillar/finance");
    await expect(page.getByTestId("forbidden")).toBeVisible();
  });

  test("logout returns to login", { tag: "@mock" }, async ({ page }) => {
    await loginAs(page, "ceo@abc.demo");
    await page.getByTestId("avatar").click();
    await page.getByTestId("logout").click();
    await expect(page).toHaveURL(/\/login/);
  });
});

/**
 * T-609 / TC-M11-15 — login + navigation for the 7 v3 roles on the real stack (02 §2, R-DEC-08).
 * Six human roles sign in with their dev password (seed v3, 08 §2.1); ROLE-AI is a service
 * account and must be refused (R-DEC-27). Real-only: the role codes come from EP-02.
 */
const ROLES = [
  ["CEO", "ceo@abc.demo", "nav-admin", "/admin/audit"],
  ["DIR", "cfo@abc.demo", "nav-business", "/admin"],
  ["MGR", "manager@abc.demo", "nav-work", "/home/pillar/finance"],
  ["EMP", "employee@abc.demo", "nav-goals", "/data/review"],
  ["REV", "reviewer@abc.demo", "nav-data", "/goals"],
  ["ADM", "admin@abc.demo", "nav-admin", "/business"],
] as const;

test.describe("7 roles on the real stack (TC-M11-15)", () => {
  for (const [role, email, allowed, denied] of ROLES) {
    test(`${role} (${email}) logs in, navigates, is denied ${denied}`, async ({ page }) => {
      await login(page, email);
      await expect(page).toHaveURL(/\/home$/);
      const session = await (await page.request.get("/api/auth/session")).json();
      expect(session.user.role).toBe(role);
      await page.getByTestId(allowed).click();
      await expect(page).toHaveURL(new RegExp(`/${allowed.slice(4)}`));
      await expect(page.getByTestId("forbidden")).toHaveCount(0);
      await page.goto(denied);
      await expect(page.getByTestId("forbidden")).toBeVisible();
    });
  }

  test("AI (ai-agent@abc.demo) is a service account — password login refused", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("Email").fill("ai-agent@abc.demo");
    await page.getByLabel("Mật khẩu").fill("any-password-1");
    await page.getByRole("button", { name: "Đăng nhập" }).click();
    await expect(page.getByTestId("login-error")).toContainText("Email hoặc mật khẩu không đúng");
    await expect(page).toHaveURL(/\/login/);
  });
});


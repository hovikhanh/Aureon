import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { cleanup, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithIntl } from "@/test/render";
import LoginPage from "@/app/login/page";
import { AuthContext, type AuthContextValue } from "./auth-context";
import type { RoleCode } from "@aureon/shared-types";
import type { AuthSession, AuthUser } from "./types";
import axe from "axe-core";

function mockUser(roleCode: RoleCode): AuthUser {
  return {
    id: "usr-1",
    email: `${roleCode.toLowerCase()}@abc.demo`,
    full_name: "Test User",
    salutation: "anh",
    role: {
      id: "role-1",
      code: roleCode,
      name_i18n_key: "shell.roles.CEO",
      pillar_scope: ["FIN"],
      pillar_agg_scope: [],
      review_pillars: [],
      can_view_salary: false,
      home_route: "/dashboard",
    },
    is_demo_account: true,
    created_at: new Date().toISOString(),
    last_login_at: null,
  };
}

function mockSession(roleCode: RoleCode): AuthSession {
  return {
    accessToken: "fake-jwt-token",
    expiresAt: new Date(Date.now() + 3600000).toISOString(),
    user: mockUser(roleCode),
    homeRoute: "/dashboard",
  };
}

describe("SCR-13 Login Page (06 §4.10, US-DC-001, T-106)", () => {
  beforeEach(() => {
    process.env.NEXT_PUBLIC_DEMO_MODE = "true";
    // Demo quick-login reads passwords from NEXT_PUBLIC_DEMO_PASSWORD_* (demo mode only).
    process.env.NEXT_PUBLIC_DEMO_PASSWORD_CEO = "demo-ceo-pw";
    process.env.NEXT_PUBLIC_DEMO_PASSWORD_CFO = "demo-cfo-pw";
    process.env.NEXT_PUBLIC_DEMO_PASSWORD_SALES = "demo-sales-pw";
    process.env.NEXT_PUBLIC_DEMO_PASSWORD_HR = "demo-hr-pw";
    process.env.NEXT_PUBLIC_DEMO_PASSWORD_REVIEWER = "demo-reviewer-pw";
  });

  afterEach(() => {
    cleanup();
    delete process.env.NEXT_PUBLIC_DEMO_PASSWORD_CEO;
    delete process.env.NEXT_PUBLIC_DEMO_PASSWORD_CFO;
    delete process.env.NEXT_PUBLIC_DEMO_PASSWORD_SALES;
    delete process.env.NEXT_PUBLIC_DEMO_PASSWORD_HR;
    delete process.env.NEXT_PUBLIC_DEMO_PASSWORD_REVIEWER;
  });

  it("renders login form with inputs and submit button", () => {
    const authValue: AuthContextValue = {
      session: null,
      user: null,
      role: "ROLE-01",
      isAuthenticated: false,
      isLoading: false,
      login: vi.fn(),
      switchRole: vi.fn(),
      logout: vi.fn(),
      setSession: vi.fn(),
    };

    renderWithIntl(
      <AuthContext.Provider value={authValue}>
        <LoginPage />
      </AuthContext.Provider>,
    );

    expect(screen.getByLabelText(/Email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Mật khẩu/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Đăng nhập/i })).toBeInTheDocument();
  });

  it("shows error when submitting empty fields", async () => {
    const user = userEvent.setup();
    const loginMock = vi.fn();
    const authValue: AuthContextValue = {
      session: null,
      user: null,
      role: "ROLE-01",
      isAuthenticated: false,
      isLoading: false,
      login: loginMock,
      switchRole: vi.fn(),
      logout: vi.fn(),
      setSession: vi.fn(),
    };

    renderWithIntl(
      <AuthContext.Provider value={authValue}>
        <LoginPage />
      </AuthContext.Provider>,
    );

    const submitBtn = screen.getByRole("button", { name: /^Đăng nhập/i });
    await user.click(submitBtn);

    expect(screen.getByRole("alert")).toHaveTextContent("Email hoặc mật khẩu không đúng");
    expect(loginMock).not.toHaveBeenCalled();
  });

  it("calls login with credentials on form submit", async () => {
    const user = userEvent.setup();
    const loginMock = vi.fn().mockResolvedValue(mockSession("ROLE-01"));
    const authValue: AuthContextValue = {
      session: null,
      user: null,
      role: "ROLE-01",
      isAuthenticated: false,
      isLoading: false,
      login: loginMock,
      switchRole: vi.fn(),
      logout: vi.fn(),
      setSession: vi.fn(),
    };

    renderWithIntl(
      <AuthContext.Provider value={authValue}>
        <LoginPage />
      </AuthContext.Provider>,
    );

    const emailInput = screen.getByLabelText(/Email/i);
    const passwordInput = screen.getByLabelText(/Mật khẩu/i);
    const submitBtn = screen.getByRole("button", { name: /^Đăng nhập/i });

    await user.type(emailInput, "ceo@abc.demo");
    await user.type(passwordInput, "correct-password");
    await user.click(submitBtn);

    expect(loginMock).toHaveBeenCalledWith("ceo@abc.demo", "correct-password");
  });

  it("displays generic error message on login rejection without enumerating users", async () => {
    const user = userEvent.setup();
    const loginMock = vi.fn().mockRejectedValue(new Error("INVALID_CREDENTIALS"));
    const authValue: AuthContextValue = {
      session: null,
      user: null,
      role: "ROLE-01",
      isAuthenticated: false,
      isLoading: false,
      login: loginMock,
      switchRole: vi.fn(),
      logout: vi.fn(),
      setSession: vi.fn(),
    };

    renderWithIntl(
      <AuthContext.Provider value={authValue}>
        <LoginPage />
      </AuthContext.Provider>,
    );

    const emailInput = screen.getByLabelText(/Email/i);
    const passwordInput = screen.getByLabelText(/Mật khẩu/i);
    const submitBtn = screen.getByRole("button", { name: /^Đăng nhập/i });

    await user.type(emailInput, "nonexistent@abc.demo");
    await user.type(passwordInput, "wrong-password");
    await user.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Email hoặc mật khẩu không đúng");
    });
  });

  it("TC-AUTH-001: shows quick-login list with 5 demo accounts and allows 1-click login", async () => {
    const user = userEvent.setup();
    const loginMock = vi.fn().mockResolvedValue(mockSession("ROLE-01"));
    const authValue: AuthContextValue = {
      session: null,
      user: null,
      role: "ROLE-01",
      isAuthenticated: false,
      isLoading: false,
      login: loginMock,
      switchRole: vi.fn(),
      logout: vi.fn(),
      setSession: vi.fn(),
    };

    renderWithIntl(
      <AuthContext.Provider value={authValue}>
        <LoginPage />
      </AuthContext.Provider>,
    );

    // Verify 5 quick demo login buttons are present
    const demoButtons = screen.getAllByRole("button", { name: /Đăng nhập với vai trò/i });
    expect(demoButtons).toHaveLength(5);

    // Click CEO demo account
    await user.click(demoButtons[0]);

    expect(loginMock).toHaveBeenCalledWith("ceo@abc.demo", expect.any(String));
  });

  it("passes axe accessibility checks without serious or critical violations", async () => {
    const authValue: AuthContextValue = {
      session: null,
      user: null,
      role: "ROLE-01",
      isAuthenticated: false,
      isLoading: false,
      login: vi.fn(),
      switchRole: vi.fn(),
      logout: vi.fn(),
      setSession: vi.fn(),
    };

    const { container } = renderWithIntl(
      <AuthContext.Provider value={authValue}>
        <LoginPage />
      </AuthContext.Provider>,
    );

    const results = await axe.run(container, {
      rules: { "color-contrast": { enabled: false } },
    });
    const seriousOrCritical = results.violations.filter((v) =>
      ["serious", "critical"].includes(v.impact ?? ""),
    );
    expect(seriousOrCritical).toEqual([]);
  });
});

import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { cleanup, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithIntl } from "@/test/render";
import { RoleSwitcher } from "@/components/layout/RoleSwitcher";
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
      name_i18n_key: `shell.roles.${roleCode === "ROLE-01" ? "CEO" : "CFO"}`,
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

describe("SCR-12 Role Switcher (06 §4.9, 02 §5, T-107)", () => {
  const originalEnv = process.env.NEXT_PUBLIC_DEMO_MODE;

  beforeEach(() => {
    process.env.NEXT_PUBLIC_DEMO_MODE = "true";
  });

  afterEach(() => {
    cleanup();
  });

  it("TC-AUTH-017: does not render when NEXT_PUBLIC_DEMO_MODE is 'false'", () => {
    process.env.NEXT_PUBLIC_DEMO_MODE = "false";
    const { container } = renderWithIntl(<RoleSwitcher />);
    expect(container.firstChild).toBeNull();
    process.env.NEXT_PUBLIC_DEMO_MODE = originalEnv;
  });

  it("renders active role and opens menu on click", async () => {
    const user = userEvent.setup();
    const session = mockSession("ROLE-01");
    const switchRoleMock = vi.fn().mockResolvedValue(mockSession("ROLE-02"));

    const authValue: AuthContextValue = {
      session,
      user: session.user,
      role: "ROLE-01",
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      switchRole: switchRoleMock,
      logout: vi.fn(),
      setSession: vi.fn(),
    };

    renderWithIntl(
      <AuthContext.Provider value={authValue}>
        <RoleSwitcher />
      </AuthContext.Provider>,
    );

    const trigger = screen.getByRole("button", { name: /Vai trò hiện tại/i });
    expect(trigger).toBeInTheDocument();
    expect(trigger).toHaveAttribute("aria-expanded", "false");

    await user.click(trigger);
    expect(trigger).toHaveAttribute("aria-expanded", "true");

    // All 5 roles should be listed in menu
    const menuItems = screen.getAllByRole("menuitem");
    expect(menuItems).toHaveLength(5);
  });

  it("TC-AUTH-016 & TC-KPI-002: selects a different role, calls switchRole and finishes ≤ 2000ms", async () => {
    const user = userEvent.setup();
    const session = mockSession("ROLE-01");
    const switchRoleMock = vi.fn().mockImplementation(async (targetRole: RoleCode) => {
      // Simulate network latency (50ms)
      await new Promise((r) => setTimeout(r, 50));
      return mockSession(targetRole);
    });

    const authValue: AuthContextValue = {
      session,
      user: session.user,
      role: "ROLE-01",
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      switchRole: switchRoleMock,
      logout: vi.fn(),
      setSession: vi.fn(),
    };

    renderWithIntl(
      <AuthContext.Provider value={authValue}>
        <RoleSwitcher />
      </AuthContext.Provider>,
    );

    const trigger = screen.getByRole("button", { name: /Vai trò hiện tại/i });
    await user.click(trigger);

    const start = performance.now();
    const cfoOption = screen.getByRole("menuitem", { name: /Giám đốc tài chính|ROLE-02/i });
    await user.click(cfoOption);

    await waitFor(() => {
      expect(switchRoleMock).toHaveBeenCalledWith("ROLE-02");
    });
    const duration = performance.now() - start;
    // TC-KPI-002: KPI must be <= 2000ms
    expect(duration).toBeLessThanOrEqual(2000);
  });

  it("passes axe accessibility checks without serious or critical violations", async () => {
    const session = mockSession("ROLE-01");
    const authValue: AuthContextValue = {
      session,
      user: session.user,
      role: "ROLE-01",
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      switchRole: vi.fn(),
      logout: vi.fn(),
      setSession: vi.fn(),
    };

    const { container } = renderWithIntl(
      <AuthContext.Provider value={authValue}>
        <RoleSwitcher />
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

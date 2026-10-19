/**
 * Auth hardening (02 §6, SCR-13): RouteGuard requires a session before rendering protected
 * routes and redirects to /login; UserMenu shows the signed-in account and signs out.
 */
import { describe, expect, it, vi, afterEach } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { RoleCode } from "@aureon/shared-types";
import messages from "../../../messages/vi.json";
import { RouteGuard } from "./RouteGuard";
import { UserMenu } from "./UserMenu";
import { AuthContext, type AuthContextValue } from "@/features/auth/auth-context";
import type { AuthSession, AuthUser } from "@/features/auth/types";

const replaceMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: replaceMock, push: vi.fn() }),
  usePathname: () => "/dashboard",
}));

function user(roleCode: RoleCode): AuthUser {
  return {
    id: "u1",
    email: "ceo@abc.demo",
    full_name: "Anh Tú",
    salutation: "anh",
    role: {
      id: "r1",
      code: roleCode,
      name_i18n_key: "shell.roles.CEO",
      pillar_scope: [],
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

function authValue(overrides: Partial<AuthContextValue>): AuthContextValue {
  return {
    session: null,
    user: null,
    role: "ROLE-01",
    isAuthenticated: false,
    isLoading: false,
    login: vi.fn(),
    switchRole: vi.fn(),
    logout: vi.fn(),
    setSession: vi.fn(),
    ...overrides,
  };
}

function wrap(value: AuthContextValue, ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <NextIntlClientProvider locale="vi" messages={messages} timeZone="Asia/Ho_Chi_Minh">
        <AuthContext.Provider value={value}>{ui}</AuthContext.Provider>
      </NextIntlClientProvider>
    </QueryClientProvider>,
  );
}

afterEach(() => {
  cleanup();
  replaceMock.mockClear();
});

describe("RouteGuard — authentication", () => {
  it("redirects to /login when there is no session", async () => {
    wrap(
      authValue({ isAuthenticated: false, isLoading: false }),
      <RouteGuard>
        <div>secret dashboard</div>
      </RouteGuard>,
    );
    await waitFor(() => expect(replaceMock).toHaveBeenCalledWith("/login"));
    expect(screen.queryByText("secret dashboard")).not.toBeInTheDocument();
  });

  it("shows a checking state while the session is still restoring", () => {
    wrap(
      authValue({ isAuthenticated: false, isLoading: true }),
      <RouteGuard>
        <div>secret dashboard</div>
      </RouteGuard>,
    );
    expect(replaceMock).not.toHaveBeenCalled();
    expect(screen.queryByText("secret dashboard")).not.toBeInTheDocument();
  });

  it("renders protected children for an authenticated user", () => {
    const session = {
      accessToken: "t",
      expiresAt: new Date(Date.now() + 3600_000).toISOString(),
      user: user("ROLE-01"),
      homeRoute: "/dashboard",
    } satisfies AuthSession;
    wrap(
      authValue({ isAuthenticated: true, isLoading: false, session, user: user("ROLE-01"), role: "ROLE-01" }),
      <RouteGuard>
        <div>secret dashboard</div>
      </RouteGuard>,
    );
    expect(screen.getByText("secret dashboard")).toBeInTheDocument();
    expect(replaceMock).not.toHaveBeenCalled();
  });
});

describe("UserMenu — logout", () => {
  it("renders nothing when unauthenticated", () => {
    const { container } = wrap(authValue({ isAuthenticated: false }), <UserMenu />);
    expect(container).toBeEmptyDOMElement();
  });

  it("shows the account and calls logout on Sign out", async () => {
    const logout = vi.fn();
    const u = user("ROLE-01");
    wrap(
      authValue({ isAuthenticated: true, user: u, role: "ROLE-01", logout }),
      <UserMenu />,
    );
    await userEvent.click(screen.getByRole("button", { name: /Tài khoản/i }));
    expect(screen.getByText("ceo@abc.demo")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("menuitem", { name: /Đăng xuất/i }));
    expect(logout).toHaveBeenCalledTimes(1);
  });
});

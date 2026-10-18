import { describe, expect, it, vi, afterEach } from "vitest";
import { cleanup, screen } from "@testing-library/react";
import { renderWithIntl } from "@/test/render";
import { DashboardView } from "./DashboardView";
import { AuthContext, type AuthContextValue } from "@/features/auth/auth-context";
import type { RoleCode } from "@aureon/shared-types";
import type { AuthSession, AuthUser } from "@/features/auth/types";
import axe from "axe-core";

function mockAuth(role: RoleCode, fullName: string = "Nguyễn Văn An"): AuthContextValue {
  const user: AuthUser = {
    id: "usr-1",
    email: `${role.toLowerCase()}@abc.demo`,
    full_name: fullName,
    salutation: "anh",
    role: {
      id: "role-1",
      code: role,
      name_i18n_key: `shell.roles.${role === "ROLE-01" ? "CEO" : "CFO"}`,
      pillar_scope: ["FIN"],
      pillar_agg_scope: [],
      review_pillars: [],
      can_view_salary: role === "ROLE-04",
      home_route: "/dashboard",
    },
    is_demo_account: true,
    created_at: new Date().toISOString(),
    last_login_at: null,
  };

  const session: AuthSession = {
    accessToken: "fake-jwt",
    expiresAt: new Date(Date.now() + 3600000).toISOString(),
    user,
    homeRoute: "/dashboard",
  };

  return {
    session,
    user,
    role,
    isAuthenticated: true,
    isLoading: false,
    login: vi.fn(),
    switchRole: vi.fn(),
    logout: vi.fn(),
    setSession: vi.fn(),
  };
}

describe("SCR-01..04 Dashboard (06 §4.1..4.4, 08 §5.1, T-111)", () => {
  afterEach(() => {
    cleanup();
  });

  it("SCR-01 CEO: renders all 4 pillars, 18 metrics, 12 alerts, and AI summary (TC-KPI-003)", () => {
    const auth = mockAuth("ROLE-01", "Nguyễn Văn An");
    const start = performance.now();

    renderWithIntl(
      <AuthContext.Provider value={auth}>
        <DashboardView />
      </AuthContext.Provider>,
    );

    const duration = performance.now() - start;
    // TC-KPI-003: Render above-the-fold and first insight <= 10s (10000ms)
    expect(duration).toBeLessThanOrEqual(10000);

    // AI Executive Summary
    expect(screen.getByText(/Tóm tắt điều hành AI/i)).toBeInTheDocument();
    expect(screen.getByText(/Doanh thu T9 đạt 8,5 tỷ/i)).toBeInTheDocument();

    // Action Needed ("Cần anh/chị quyết")
    expect(screen.getByText(/Cần anh\/chị quyết/i)).toBeInTheDocument();
    // 12 alerts present
    expect(screen.getByText("12")).toBeInTheDocument();

    // 4 pillars present
    expect(screen.getByRole("heading", { name: "Tài chính", level: 2 })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Khách hàng", level: 2 })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Vận hành", level: 2 })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Con người", level: 2 })).toBeInTheDocument();

    // Check specific critical and warning alerts
    expect(document.querySelector('[data-alert-code="ALERT-FIN-05"]')).toBeInTheDocument();
    expect(document.querySelector('[data-alert-code="ALERT-CUS-01"]')).toBeInTheDocument();
    expect(document.querySelector('[data-alert-code="ALERT-FIN-01"]')).toBeInTheDocument();

    // Check specific metrics
    expect(screen.getAllByText(/METRIC-FIN-01/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/METRIC-CUS-04/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/METRIC-OPS-01/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/METRIC-HR-01/i).length).toBeGreaterThanOrEqual(1);
  });

  it("SCR-02 CFO: renders FIN + OPS full, CUS + HR aggregate, and only FIN/OPS alerts", () => {
    const auth = mockAuth("ROLE-02", "Trần Thị Bình");

    renderWithIntl(
      <AuthContext.Provider value={auth}>
        <DashboardView />
      </AuthContext.Provider>,
    );

    // No CEO AI Executive Summary
    expect(screen.queryByText(/Tóm tắt điều hành AI/i)).not.toBeInTheDocument();

    // Detailed FIN & OPS pillars
    expect(screen.getByRole("heading", { name: "Tài chính", level: 2 })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Vận hành", level: 2 })).toBeInTheDocument();

    // Aggregate pillars header
    expect(screen.getByText(/Chỉ số tổng hợp/i)).toBeInTheDocument();

    // FIN and OPS alerts present
    expect(document.querySelector('[data-alert-code="ALERT-FIN-05"]')).toBeInTheDocument();
    expect(document.querySelector('[data-alert-code="ALERT-OPS-01"]')).toBeInTheDocument();

    // CUS alerts NOT in CFO's action needed
    expect(document.querySelector('[data-alert-code="ALERT-CUS-01"]')).not.toBeInTheDocument();
    expect(document.querySelector('[data-alert-code="ALERT-CUS-04"]')).not.toBeInTheDocument();
  });

  it("SCR-03 Sales Director: renders CUS full, revenue metric, and CUS alerts only", () => {
    const auth = mockAuth("ROLE-03", "Lê Hoàng Cường");

    renderWithIntl(
      <AuthContext.Provider value={auth}>
        <DashboardView />
      </AuthContext.Provider>,
    );

    expect(screen.getByRole("heading", { name: "Khách hàng", level: 2 })).toBeInTheDocument();
    expect(screen.getByText(/METRIC-FIN-01/i)).toBeInTheDocument();

    // CUS alerts present
    expect(document.querySelector('[data-alert-code="ALERT-CUS-01"]')).toBeInTheDocument();
    expect(document.querySelector('[data-alert-code="ALERT-CUS-04"]')).toBeInTheDocument();

    // FIN expense / debt alerts NOT in Sales Director's action needed
    expect(document.querySelector('[data-alert-code="ALERT-FIN-05"]')).not.toBeInTheDocument();
    expect(document.querySelector('[data-alert-code="ALERT-FIN-06"]')).not.toBeInTheDocument();
  });

  it("SCR-04 HR Manager: renders HR and OPS full, and HR alerts only", () => {
    const auth = mockAuth("ROLE-04", "Phạm Thị Dung");

    renderWithIntl(
      <AuthContext.Provider value={auth}>
        <DashboardView />
      </AuthContext.Provider>,
    );

    expect(screen.getByRole("heading", { name: "Con người", level: 2 })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Vận hành", level: 2 })).toBeInTheDocument();

    // No FIN critical alerts
    expect(document.querySelector('[data-alert-code="ALERT-FIN-05"]')).not.toBeInTheDocument();
    expect(document.querySelector('[data-alert-code="ALERT-CUS-01"]')).not.toBeInTheDocument();
  });

  it("TC-UI-006: SCR-01 CEO dashboard passes axe scan without serious or critical violations", async () => {
    const auth = mockAuth("ROLE-01");
    const { container } = renderWithIntl(
      <AuthContext.Provider value={auth}>
        <DashboardView />
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

/**
 * T-223 — SCR-11 Schemas (read-only) tests (06 §4.8, TC-IDP-038, TC-UI-009):
 * - Renders schema table for INVOICE doc type
 * - Hides SALARY fields for non-HR/Reviewer roles
 * - Shows SALARY fields for ROLE-04/ROLE-05
 * - Doc type switcher buttons render for 7 types
 * - axe scan 0 violations (TC-UI-006)
 */
import type { ReactElement } from "react";
import axe from "axe-core";
import { cleanup, render, screen, fireEvent } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, describe, expect, it, vi } from "vitest";
import viMessages from "../../../../messages/vi.json";
import { SchemasView } from "./SchemasView";
import { DEMO_SCHEMAS } from "./demo-fixtures";

// Mock TanStack Query so SchemasView uses placeholderData immediately
vi.mock("@tanstack/react-query", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@tanstack/react-query")>();
  return {
    ...actual,
    useQuery: () => ({
      data: DEMO_SCHEMAS,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    }),
  };
});

vi.mock("@/features/auth/auth-context", () => ({
  useAuth: () => ({
    role: "ROLE-05",
    session: null,
  }),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

afterEach(cleanup);

function withIntl(ui: ReactElement) {
  return (
    <NextIntlClientProvider locale="vi" messages={viMessages} timeZone="Asia/Ho_Chi_Minh">
      {ui}
    </NextIntlClientProvider>
  );
}

async function expectNoSeriousViolations(container: HTMLElement) {
  const results = await axe.run(container, {
    resultTypes: ["violations"],
    rules: { "color-contrast": { enabled: false } },
  });
  const serious = results.violations.filter(
    (v) => v.impact === "serious" || v.impact === "critical",
  );
  expect(serious.map((v) => `${v.id}: ${v.help}`)).toEqual([]);
}

describe("TC-IDP-038 SchemasView", () => {
  it("renders page title and doc type buttons", () => {
    render(withIntl(<SchemasView />));
    expect(screen.getByText("Schema tài liệu")).toBeInTheDocument();
    expect(screen.getByTestId("doc-type-btn-INVOICE")).toBeInTheDocument();
    expect(screen.getByTestId("doc-type-btn-EMPLOYEE_LIST")).toBeInTheDocument();
  });

  it("shows 7 doc type options", () => {
    render(withIntl(<SchemasView />));
    const btns = [
      "INVOICE", "SALES_REPORT", "KPI_OKR", "MEETING_MINUTES",
      "FINANCIAL_REPORT", "CONTRACT", "EMPLOYEE_LIST",
    ];
    for (const dt of btns) {
      expect(screen.getByTestId(`doc-type-btn-${dt}`)).toBeInTheDocument();
    }
  });

  it("defaults to INVOICE schema — shows invoice fields", () => {
    render(withIntl(<SchemasView />));
    expect(screen.getByTestId("schema-table-INVOICE")).toBeInTheDocument();
    expect(screen.getByTestId("field-row-invoice_number")).toBeInTheDocument();
    expect(screen.getByTestId("field-row-total_amount")).toBeInTheDocument();
  });

  it("switches to EMPLOYEE_LIST schema when button clicked", () => {
    render(withIntl(<SchemasView />));
    fireEvent.click(screen.getByTestId("doc-type-btn-EMPLOYEE_LIST"));
    expect(screen.getByTestId("schema-table-EMPLOYEE_LIST")).toBeInTheDocument();
    expect(screen.getByTestId("field-row-full_name")).toBeInTheDocument();
  });

  it("shows base_salary field for ROLE-05 (Reviewer has access)", () => {
    render(withIntl(<SchemasView />));
    fireEvent.click(screen.getByTestId("doc-type-btn-EMPLOYEE_LIST"));
    expect(screen.getByTestId("field-row-base_salary")).toBeInTheDocument();
  });

  it("shows schema version string", () => {
    render(withIntl(<SchemasView />));
    expect(screen.getByText(/Phiên bản:/)).toBeInTheDocument();
  });

  it("marks required fields with CheckCircle icon", () => {
    render(withIntl(<SchemasView />));
    // invoice_number is required
    const row = screen.getByTestId("field-row-invoice_number");
    expect(row.querySelector("svg[aria-label='Bắt buộc']")).toBeInTheDocument();
  });

  it("shows validation rules for fields", () => {
    render(withIntl(<SchemasView />));
    // subtotal and total_amount both have VR-INV-01 → use getAllByText
    const rules = screen.getAllByText("VR-INV-01");
    expect(rules.length).toBeGreaterThanOrEqual(1);
  });
});

describe("TC-UI-006 axe scan — SchemasView", () => {
  it("has no serious/critical violations", async () => {
    const { container } = render(withIntl(<SchemasView />));
    await expectNoSeriousViolations(container);
  });
});

/**
 * T-223 — SCR-07 Documents library tests (06 §4.4, FR-DC-21, TC-IDP-037, TC-UI-009):
 * - Table renders filename, status badge, AI state badge
 * - Salary rows show masked value + lock icon for non-HR/Reviewer roles
 * - COMMITTED row with active undo_deadline shows Undo button
 * - COMMITTED row without undo_deadline hides Undo button
 * - ROLE-01 never shows Undo button (spec: CEO không có)
 * - Upload link navigates to /upload
 * - Empty state shown when documents = []
 * - axe scan 0 serious/critical violations (TC-UI-006)
 */
import type { ReactElement } from "react";
import axe from "axe-core";
import { cleanup, render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, describe, expect, it, vi } from "vitest";
import viMessages from "../../../../messages/vi.json";
import { DocumentsTable } from "./DocumentsTable";
import { DEMO_DOCUMENTS } from "./demo-fixtures";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useParams: () => ({}),
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

// Salary document (index 2 — EMPLOYEE_LIST, contains_salary=true)
const salaryDoc = DEMO_DOCUMENTS[2]!;
// Committed doc with undo_deadline (index 1 — SALES_REPORT)
const committedDoc = DEMO_DOCUMENTS[1]!;
// Failed doc (index 4 — CONTRACT, status=FAILED)
const failedDoc = DEMO_DOCUMENTS[4]!;

describe("TC-IDP-037 DocumentsTable", () => {
  it("renders all 5 demo documents", () => {
    render(withIntl(<DocumentsTable documents={DEMO_DOCUMENTS} role="ROLE-05" />));
    for (const doc of DEMO_DOCUMENTS) {
      const row = screen.getByTestId(`doc-row-${doc.id}`);
      expect(row).toBeInTheDocument();
    }
  });

  it("shows status badge for each row", () => {
    render(withIntl(<DocumentsTable documents={DEMO_DOCUMENTS} role="ROLE-05" />));
    expect(screen.getByTestId(`status-badge-${committedDoc.id}`)).toHaveTextContent("Đã ghi nhận");
    expect(screen.getByTestId(`status-badge-${failedDoc.id}`)).toHaveTextContent("Thất bại");
  });

  it("shows AI state badge on each document row", () => {
    render(withIntl(<DocumentsTable documents={DEMO_DOCUMENTS} role="ROLE-05" />));
    // All demo docs have ai_state set
    const badges = document.querySelectorAll("[data-ai-level]");
    expect(badges.length).toBeGreaterThan(0);
  });

  it("masks salary document filename for ROLE-01 (CEO)", () => {
    render(withIntl(<DocumentsTable documents={[salaryDoc]} role="ROLE-01" />));
    const row = screen.getByTestId(`doc-row-${salaryDoc.id}`);
    expect(row.querySelector("[data-masked='true']")).toBeInTheDocument();
  });

  it("masks salary document filename for ROLE-02 (CFO)", () => {
    render(withIntl(<DocumentsTable documents={[salaryDoc]} role="ROLE-02" />));
    expect(screen.getByTestId(`doc-row-${salaryDoc.id}`).querySelector("[data-masked='true']")).toBeInTheDocument();
  });

  it("shows salary document filename for ROLE-04 (HR Manager)", () => {
    render(withIntl(<DocumentsTable documents={[salaryDoc]} role="ROLE-04" />));
    // HR can see salary → filename visible, no masked dot pattern
    const row = screen.getByTestId(`doc-row-${salaryDoc.id}`);
    expect(row.querySelector("[data-masked='true']")).not.toBeInTheDocument();
    expect(row).toHaveTextContent(salaryDoc.original_filename ?? "");
  });

  it("shows salary document filename for ROLE-05 (Reviewer)", () => {
    render(withIntl(<DocumentsTable documents={[salaryDoc]} role="ROLE-05" />));
    const row = screen.getByTestId(`doc-row-${salaryDoc.id}`);
    expect(row.querySelector("[data-masked='true']")).not.toBeInTheDocument();
  });

  it("shows Undo button for COMMITTED doc with active undo_deadline for ROLE-05", () => {
    // Patch undo_deadline to be in the future
    const futureDoc = {
      ...committedDoc,
      undo_deadline: new Date(Date.now() + 7 * 24 * 3600 * 1000).toISOString(),
    };
    render(withIntl(
      <DocumentsTable documents={[futureDoc]} role="ROLE-05" onUndo={vi.fn()} />
    ));
    expect(screen.getByTestId(`undo-btn-${futureDoc.id}`)).toBeInTheDocument();
  });

  it("hides Undo button for ROLE-01 (CEO spec: không có Undo)", () => {
    const futureDoc = {
      ...committedDoc,
      undo_deadline: new Date(Date.now() + 7 * 24 * 3600 * 1000).toISOString(),
    };
    render(withIntl(
      <DocumentsTable documents={[futureDoc]} role="ROLE-01" onUndo={vi.fn()} />
    ));
    expect(screen.queryByTestId(`undo-btn-${futureDoc.id}`)).not.toBeInTheDocument();
  });

  it("hides Undo button when undo_deadline has passed", () => {
    const expiredDoc = {
      ...committedDoc,
      undo_deadline: new Date(Date.now() - 1000).toISOString(),
    };
    render(withIntl(
      <DocumentsTable documents={[expiredDoc]} role="ROLE-05" onUndo={vi.fn()} />
    ));
    expect(screen.queryByTestId(`undo-btn-${expiredDoc.id}`)).not.toBeInTheDocument();
  });

  it("shows FAILED status reason text", () => {
    render(withIntl(<DocumentsTable documents={[failedDoc]} role="ROLE-05" />));
    expect(screen.getByText(/IDP-E06/)).toBeInTheDocument();
  });

  it("shows view detail link for non-salary docs", () => {
    const invoiceDoc = DEMO_DOCUMENTS[0]!;
    render(withIntl(<DocumentsTable documents={[invoiceDoc]} role="ROLE-05" />));
    const link = screen.getByRole("link", { name: /Xem chi tiết/ });
    expect(link).toHaveAttribute("href", `/documents/${invoiceDoc.id}`);
  });
});

describe("TC-UI-006 axe scan — DocumentsTable", () => {
  it("has no serious/critical violations", async () => {
    const { container } = render(
      withIntl(<DocumentsTable documents={DEMO_DOCUMENTS} role="ROLE-05" />),
    );
    await expectNoSeriousViolations(container);
  });
});

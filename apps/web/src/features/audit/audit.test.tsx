/**
 * T-404 — SCR-14 Audit log tests (06 §4.11, EP-52, FR-DC-22, TC-AUDIT-FE-001):
 * - Table renders occurred_at, actor name, action, target
 * - AI actor row shows the "AI (IDP)" label, not a user name
 * - Salary value in before/after displays the server-side mask verbatim (never a number)
 * - axe scan: 0 serious/critical violations
 */
import type { ReactElement } from "react";
import axe from "axe-core";
import { cleanup, render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, describe, expect, it } from "vitest";
import type { AuditLogOut } from "@aureon/shared-types";
import viMessages from "../../../messages/vi.json";
import { AuditLogTable } from "./AuditLogTable";

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

const ROWS: AuditLogOut[] = [
  {
    id: "11111111-1111-1111-1111-111111111111",
    occurred_at: "2026-10-19T08:30:00Z",
    actor_type: "USER",
    actor: { id: "u1", full_name: "Trần Thị CEO" },
    actor_role_code: "ROLE-01",
    action: "auth.switch_role",
    target_type: "users",
    target_id: "22222222-2222-2222-2222-222222222222",
    source_document_id: null,
    before: { role: "ROLE-01" },
    after: { role: "ROLE-02" },
    metadata: null,
  },
  {
    id: "33333333-3333-3333-3333-333333333333",
    occurred_at: "2026-10-19T09:00:00Z",
    actor_type: "AI",
    actor: null,
    actor_role_code: null,
    action: "ai.classify",
    target_type: "source_documents",
    target_id: null,
    source_document_id: "44444444-4444-4444-4444-444444444444",
    before: null,
    after: { doc_type: "INVOICE" },
    metadata: null,
  },
  {
    id: "55555555-5555-5555-5555-555555555555",
    occurred_at: "2026-10-19T09:30:00Z",
    actor_type: "USER",
    actor: { id: "u2", full_name: "Lê Văn HR" },
    actor_role_code: "ROLE-04",
    action: "action.employee.upsert",
    target_type: "business_records",
    target_id: null,
    source_document_id: null,
    before: null,
    after: { name: "Nguyễn Văn A", salary: "••••" },
    metadata: null,
  },
];

describe("TC-AUDIT-FE-001 AuditLogTable", () => {
  it("renders actor name, action and target for a user entry", () => {
    render(withIntl(<AuditLogTable rows={ROWS} />));
    expect(screen.getByText("Trần Thị CEO")).toBeInTheDocument();
    expect(screen.getByText("auth.switch_role")).toBeInTheDocument();
    expect(screen.getAllByText("users").length).toBeGreaterThan(0);
  });

  it("labels an AI actor as AI (IDP), not a user name", () => {
    render(withIntl(<AuditLogTable rows={ROWS} />));
    expect(screen.getByText("AI (IDP)")).toBeInTheDocument();
    expect(screen.getByText("ai.classify")).toBeInTheDocument();
  });

  it("shows the server-side salary mask verbatim and never a raw number", () => {
    render(withIntl(<AuditLogTable rows={ROWS} />));
    // The masked token is rendered on the same <li> as the salary key; no raw figure.
    const salaryLi = screen.getByText(/salary:/).closest("li");
    expect(salaryLi).toHaveTextContent("••••");
    expect(screen.queryByText(/45[.,]?000[.,]?000/)).not.toBeInTheDocument();
  });

  it("has no serious or critical a11y violations", async () => {
    const { container } = render(withIntl(<AuditLogTable rows={ROWS} />));
    await expectNoSeriousViolations(container);
  });
});

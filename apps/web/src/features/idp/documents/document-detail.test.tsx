/**
 * SCR-07 Document detail (EP-25, 06 §4.4) tests:
 * - Renders metadata, status timeline, jobs, reviews
 * - Virtual (MANUAL/TRANSCRIPT) documents with null filename fall back to a label
 * - COMMITTED doc shows affected metric links (P01 drill-through)
 * - NEEDS_REVIEW doc shows "open review" action
 * - 403 scope error renders ForbiddenState
 * - axe scan 0 serious/critical violations (TC-UI-006)
 */
import type { ReactElement } from "react";
import axe from "axe-core";
import { cleanup, render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { DocumentDetailOut } from "@aureon/shared-types";
import viMessages from "../../../../messages/vi.json";
import { DocumentDetailView } from "./DocumentDetailView";

/* -------------------------------------------------------------------------- */
/* Mocks                                                                       */
/* -------------------------------------------------------------------------- */
const mockQueryState: {
  data: DocumentDetailOut | undefined;
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
} = {
  data: undefined,
  isLoading: false,
  isError: false,
  error: null,
};

vi.mock("@tanstack/react-query", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@tanstack/react-query")>();
  return {
    ...actual,
    useQuery: () => ({ ...mockQueryState, refetch: vi.fn() }),
  };
});

vi.mock("@/features/auth/auth-context", () => ({
  useAuth: () => ({ role: "ROLE-05", session: { accessToken: "tok" }, isLoading: false }),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useParams: () => ({ documentId: "doc-1" }),
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

/* -------------------------------------------------------------------------- */
/* Fixtures                                                                    */
/* -------------------------------------------------------------------------- */
const uploader = { id: "u1", full_name: "Vũ Đức Thắng" };

function makeDetail(overrides: Partial<DocumentDetailOut["document"]> = {}): DocumentDetailOut {
  return {
    document: {
      id: "doc-1",
      batch_id: null,
      channel: "C3",
      kind: "FILE",
      original_filename: "invoice-001.pdf",
      mime_type: "application/pdf",
      size_bytes: 204800,
      page_count: 2,
      doc_type: "INVOICE",
      pillars: ["FIN"],
      status: "COMMITTED",
      status_reason: null,
      ai_state: "L3",
      autonomy_level: "L3",
      contains_salary: false,
      contains_pii: false,
      duplicate_of_id: null,
      uploaded_by: uploader,
      uploaded_at: "2026-10-18T08:30:00Z",
      committed_at: "2026-10-18T09:00:00Z",
      undo_deadline: "2026-10-25T09:00:00Z",
      locked_by: null,
      locked_until: null,
      retry_count: 0,
      latest_job: null,
      ...overrides,
    },
    jobs: [
      {
        id: "job-1",
        attempt_no: 1,
        doc_type: "INVOICE",
        status: "SUCCEEDED",
        classification_confidence: 0.98,
        routing_decision: "AUTO_APPROVE",
        routing_reason: null,
        error_code: null,
        avg_confidence: 0.95,
        validation_summary: null,
        cross_doc_results: null,
        started_at: "2026-10-18T08:31:00Z",
        finished_at: "2026-10-18T08:32:00Z",
      },
    ],
    status_timeline: [
      { status: "UPLOADED", at: "2026-10-18T08:30:00Z", actor_type: "USER" },
      { status: "COMMITTED", at: "2026-10-18T09:00:00Z", actor_type: "SYSTEM" },
    ],
    affected: {
      business_record_ids: ["br-1"],
      metric_codes: ["METRIC-FIN-01"],
    },
    reviews: [
      {
        reviewer_full_name: "Vũ Đức Thắng",
        decision: "APPROVED",
        reject_reason_code: null,
        decided_at: "2026-10-18T08:59:00Z",
      },
    ],
  };
}

beforeEach(() => {
  mockQueryState.data = makeDetail();
  mockQueryState.isLoading = false;
  mockQueryState.isError = false;
  mockQueryState.error = null;
});

/* -------------------------------------------------------------------------- */
/* Tests                                                                       */
/* -------------------------------------------------------------------------- */
describe("DocumentDetailView (EP-25)", () => {
  it("renders the filename and document id", () => {
    render(withIntl(<DocumentDetailView documentId="doc-1" />));
    expect(screen.getByText("invoice-001.pdf")).toBeInTheDocument();
    expect(screen.getByText("doc-1")).toBeInTheDocument();
  });

  it("renders metadata, timeline, jobs and reviews sections", () => {
    render(withIntl(<DocumentDetailView documentId="doc-1" />));
    expect(screen.getByText("Thông tin tài liệu")).toBeInTheDocument();
    expect(screen.getByText("Dòng thời gian trạng thái")).toBeInTheDocument();
    expect(screen.getByText("Lịch sử xử lý")).toBeInTheDocument();
    expect(screen.getByText("Lịch sử duyệt")).toBeInTheDocument();
    // Reviewer name shows in the review list
    expect(screen.getAllByText("Vũ Đức Thắng").length).toBeGreaterThan(0);
  });

  it("shows affected metric link for drill-through (P01)", () => {
    render(withIntl(<DocumentDetailView documentId="doc-1" />));
    const link = screen.getByRole("link", { name: /METRIC-FIN-01/ });
    expect(link).toHaveAttribute("href", "/dashboard?metric=METRIC-FIN-01");
  });

  it("falls back to a label for a virtual document with null filename", () => {
    mockQueryState.data = makeDetail({
      kind: "MANUAL",
      channel: "C1",
      original_filename: null,
      mime_type: null,
      size_bytes: null,
      page_count: null,
    });
    render(withIntl(<DocumentDetailView documentId="doc-1" />));
    // Heading uses the doc type label (Hóa đơn) instead of an empty filename
    expect(screen.getAllByText(/Hóa đơn/).length).toBeGreaterThan(0);
  });

  it("shows the open-review action for a NEEDS_REVIEW document", () => {
    mockQueryState.data = makeDetail({ status: "NEEDS_REVIEW", ai_state: "L2" });
    render(withIntl(<DocumentDetailView documentId="doc-1" />));
    const link = screen.getByRole("link", { name: /Mở trang duyệt/ });
    expect(link).toHaveAttribute("href", "/review/doc-1");
  });

  it("renders ForbiddenState on a 403 scope error", () => {
    mockQueryState.data = undefined;
    mockQueryState.isError = true;
    mockQueryState.error = new Error("403 FORBIDDEN_SCOPE");
    render(withIntl(<DocumentDetailView documentId="doc-1" />));
    expect(
      screen.getByText("Bạn không có quyền xem tài liệu này"),
    ).toBeInTheDocument();
  });

  it("has no serious/critical a11y violations", async () => {
    const { container } = render(withIntl(<DocumentDetailView documentId="doc-1" />));
    await expectNoSeriousViolations(container);
  });
});

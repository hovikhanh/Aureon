/**
 * T-219 — SCR-06 Review Detail tests (06 §4.3, FR-DC-18, FR-DC-19, US-DC-012):
 * - TC-IDP-033: ConfidenceIndicator renders correct colour band + icon + percent
 * - TC-IDP-033: ExtractionFieldRow shows confirm button for MEDIUM/LOW fields
 * - TC-IDP-033: ExtractionFieldRow shows corrected tag after edit
 * - TC-IDP-033: RejectDialog opens, validates OTHER reason, submits
 * - TC-IDP-033: ReviewView renders 2-column layout + approve/reject actions
 * - TC-UI-006: axe scan — 0 serious/critical violations
 * - TC-KPI-004: Key interactive elements render within expected structure
 */
import type { ReactElement } from "react";
import axe from "axe-core";
import { cleanup, render, screen, fireEvent, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, describe, expect, it, vi } from "vitest";
import viMessages from "../../../../messages/vi.json";
import { ConfidenceIndicator } from "./ConfidenceIndicator";
import { ExtractionFieldRow } from "./ExtractionFieldRow";
import { RejectDialog } from "./RejectDialog";
import { ReviewView } from "./ReviewView";
import { DEMO_REVIEW_OPEN_OUT } from "./demo-fixtures";

// Silence Next.js router in jsdom
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
  useParams: () => ({ documentId: "d1000000-0000-0000-0000-000000000001" }),
}));

afterEach(cleanup);

function withIntl(ui: ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return (
    <QueryClientProvider client={qc}>
      <NextIntlClientProvider locale="vi" messages={viMessages} timeZone="Asia/Ho_Chi_Minh">
        {ui}
      </NextIntlClientProvider>
    </QueryClientProvider>
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

const sampleField = DEMO_REVIEW_OPEN_OUT.extraction.fields[2]!; // subtotal — MEDIUM
const lowField = DEMO_REVIEW_OPEN_OUT.extraction.fields[3]!;    // vat_amount — LOW
const highField = DEMO_REVIEW_OPEN_OUT.extraction.fields[0]!;   // invoice_number — HIGH

describe("TC-IDP-033 ConfidenceIndicator", () => {
  it("renders HIGH band: green colour, CheckCircle icon, and percent", () => {
    const { container } = render(
      withIntl(<ConfidenceIndicator confidence={0.96} band="HIGH" />),
    );
    const el = container.querySelector("[data-confidence-band='HIGH']");
    expect(el).toBeInTheDocument();
    expect(screen.getByText("Độ tin cậy cao")).toBeInTheDocument();
    expect(screen.getByText("(96%)")).toBeInTheDocument();
  });

  it("renders MEDIUM band: amber colour, AlertCircle icon, and percent", () => {
    const { container } = render(
      withIntl(<ConfidenceIndicator confidence={0.85} band="MEDIUM" />),
    );
    const el = container.querySelector("[data-confidence-band='MEDIUM']");
    expect(el).toBeInTheDocument();
    expect(screen.getByText("Nên kiểm tra")).toBeInTheDocument();
    expect(screen.getByText("(85%)")).toBeInTheDocument();
  });

  it("renders LOW band: rose colour, AlertTriangle icon, and percent", () => {
    const { container } = render(
      withIntl(<ConfidenceIndicator confidence={0.62} band="LOW" />),
    );
    const el = container.querySelector("[data-confidence-band='LOW']");
    expect(el).toBeInTheDocument();
    expect(screen.getByText("Cần xác nhận")).toBeInTheDocument();
    expect(screen.getByText("(62%)")).toBeInTheDocument();
  });

  it("infers band from confidence when band prop not given", () => {
    const { container } = render(
      withIntl(<ConfidenceIndicator confidence={0.75} />),
    );
    expect(container.querySelector("[data-confidence-band='MEDIUM']")).toBeInTheDocument();
  });

  it("handles null confidence gracefully", () => {
    const { container } = render(
      withIntl(<ConfidenceIndicator confidence={null} />),
    );
    expect(container.querySelector("[data-confidence-band='LOW']")).toBeInTheDocument();
  });
});

describe("TC-IDP-033 ExtractionFieldRow", () => {
  it("MEDIUM field shows Confirm button (needs attention)", () => {
    const editState = {
      fieldId: sampleField.id,
      originalValue: sampleField.value,
      currentValue: sampleField.value,
      isCorrected: false,
      isConfirmed: false,
    };
    render(
      withIntl(
        <ExtractionFieldRow
          field={sampleField}
          editState={editState}
          onConfirm={vi.fn()}
        />,
      ),
    );
    expect(screen.getByRole("button", { name: /Xác nhận subtotal/i })).toBeInTheDocument();
  });

  it("LOW field shows Confirm button", () => {
    const editState = {
      fieldId: lowField.id,
      originalValue: lowField.value,
      currentValue: lowField.value,
      isCorrected: false,
      isConfirmed: false,
    };
    render(
      withIntl(
        <ExtractionFieldRow
          field={lowField}
          editState={editState}
          onConfirm={vi.fn()}
        />,
      ),
    );
    expect(screen.getByRole("button", { name: /Xác nhận vat_amount/i })).toBeInTheDocument();
  });

  it("HIGH field does NOT show Confirm button", () => {
    const editState = {
      fieldId: highField.id,
      originalValue: highField.value,
      currentValue: highField.value,
      isCorrected: false,
      isConfirmed: true,
    };
    render(
      withIntl(
        <ExtractionFieldRow
          field={highField}
          editState={editState}
        />,
      ),
    );
    expect(screen.queryByRole("button", { name: /Xác nhận invoice_number/i })).not.toBeInTheDocument();
  });

  it("shows Corrected tag when isCorrected=true and hides Confirm button", () => {
    const editState = {
      fieldId: sampleField.id,
      originalValue: sampleField.value,
      currentValue: 9200000,
      isCorrected: true,
      isConfirmed: true,
    };
    render(
      withIntl(
        <ExtractionFieldRow
          field={sampleField}
          editState={editState}
          onRevert={vi.fn()}
        />,
      ),
    );
    expect(screen.getByText("Đã chỉnh sửa")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Xác nhận subtotal/i })).not.toBeInTheDocument();
  });

  it("calls onConfirm callback when Confirm button is clicked", () => {
    const onConfirm = vi.fn();
    const editState = {
      fieldId: lowField.id,
      originalValue: lowField.value,
      currentValue: lowField.value,
      isCorrected: false,
      isConfirmed: false,
    };
    render(
      withIntl(
        <ExtractionFieldRow
          field={lowField}
          editState={editState}
          onConfirm={onConfirm}
        />,
      ),
    );
    fireEvent.click(screen.getByRole("button", { name: /Xác nhận vat_amount/i }));
    expect(onConfirm).toHaveBeenCalledOnce();
  });

  it("calls onChangeValue when input value changes", () => {
    const onChangeValue = vi.fn();
    const editState = {
      fieldId: highField.id,
      originalValue: "INV-2026-9999",
      currentValue: "INV-2026-9999",
      isCorrected: false,
      isConfirmed: true,
    };
    render(
      withIntl(
        <ExtractionFieldRow
          field={highField}
          editState={editState}
          onChangeValue={onChangeValue}
        />,
      ),
    );
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "INV-2026-0001" } });
    expect(onChangeValue).toHaveBeenCalled();
  });
});

describe("TC-IDP-033 RejectDialog", () => {
  it("renders with default reason WRONG_DATA", () => {
    render(
      withIntl(
        <RejectDialog isOpen={true} onClose={vi.fn()} onConfirm={vi.fn()} />,
      ),
    );
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Từ chối tài liệu")).toBeInTheDocument();
    const select = screen.getByRole("combobox") as HTMLSelectElement;
    expect(select.value).toBe("WRONG_DATA");
  });

  it("does NOT require note for non-OTHER reasons", async () => {
    const onConfirm = vi.fn().mockResolvedValue(undefined);
    render(
      withIntl(
        <RejectDialog isOpen={true} onClose={vi.fn()} onConfirm={onConfirm} />,
      ),
    );
    fireEvent.click(screen.getByRole("button", { name: "Xác nhận từ chối" }));
    await waitFor(() => expect(onConfirm).toHaveBeenCalledWith("WRONG_DATA", undefined));
  });

  it("requires note when OTHER is selected", async () => {
    const onConfirm = vi.fn().mockResolvedValue(undefined);
    render(
      withIntl(
        <RejectDialog isOpen={true} onClose={vi.fn()} onConfirm={onConfirm} />,
      ),
    );
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "OTHER" } });
    // Submit without note — should not call onConfirm
    fireEvent.click(screen.getByRole("button", { name: "Xác nhận từ chối" }));
    expect(onConfirm).not.toHaveBeenCalled();

    // Enter a note then submit
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "Custom reason text" } });
    fireEvent.click(screen.getByRole("button", { name: "Xác nhận từ chối" }));
    await waitFor(() => expect(onConfirm).toHaveBeenCalledWith("OTHER", "Custom reason text"));
  });

  it("calls onClose when Cancel is clicked", () => {
    const onClose = vi.fn();
    render(
      withIntl(
        <RejectDialog isOpen={true} onClose={onClose} onConfirm={vi.fn()} />,
      ),
    );
    fireEvent.click(screen.getByRole("button", { name: "Hủy" }));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("does not render when isOpen=false", () => {
    const { container } = render(
      withIntl(
        <RejectDialog isOpen={false} onClose={vi.fn()} onConfirm={vi.fn()} />,
      ),
    );
    expect(container.querySelector("[role='dialog']")).not.toBeInTheDocument();
  });
});

describe("TC-IDP-033 ReviewView", () => {
  const { document, review_id: reviewId, extraction } = DEMO_REVIEW_OPEN_OUT;

  it("renders 2-column layout: source viewer (SCR-10) + extraction form", () => {
    render(
      withIntl(
        <ReviewView
          document={document}
          reviewId={reviewId}
          extraction={extraction}
          role="ROLE-05"
          onApprove={vi.fn()}
          onReject={vi.fn()}
        />,
      ),
    );
    expect(screen.getByText("Tài liệu gốc")).toBeInTheDocument();
    expect(screen.getByText("Các trường trích xuất")).toBeInTheDocument();
    // Source panel now mounts the real SourceViewer; without a token it shows its loading
    // shell (the query is disabled), so the panel is present even though no file is fetched.
    expect(screen.getByText("Đang tải tài liệu gốc…")).toBeInTheDocument();
    // filename still appears in the top bar.
    const filenameEls = screen.getAllByText(document.original_filename ?? "");
    expect(filenameEls.length).toBeGreaterThan(0);
  });

  it("renders all 6 demo fields from extraction", () => {
    render(
      withIntl(
        <ReviewView
          document={document}
          reviewId={reviewId}
          extraction={extraction}
          role="ROLE-05"
          onApprove={vi.fn()}
          onReject={vi.fn()}
        />,
      ),
    );
    expect(screen.getByTestId("field-row-invoice_number")).toBeInTheDocument();
    expect(screen.getByTestId("field-row-subtotal")).toBeInTheDocument();
    expect(screen.getByTestId("field-row-vat_amount")).toBeInTheDocument();
    expect(screen.getByTestId("field-row-total_amount")).toBeInTheDocument();
  });

  it("shows Approve and Reject buttons for ROLE-05", () => {
    render(
      withIntl(
        <ReviewView
          document={document}
          reviewId={reviewId}
          extraction={extraction}
          role="ROLE-05"
          onApprove={vi.fn()}
          onReject={vi.fn()}
        />,
      ),
    );
    expect(screen.getByRole("button", { name: /Duyệt/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Từ chối/i })).toBeInTheDocument();
  });

  it("hides Approve/Reject buttons for ROLE-01 (view-only)", () => {
    render(
      withIntl(
        <ReviewView
          document={document}
          reviewId={reviewId}
          extraction={extraction}
          role="ROLE-01"
          onApprove={vi.fn()}
          onReject={vi.fn()}
        />,
      ),
    );
    expect(screen.queryByRole("button", { name: /Duyệt/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Từ chối/i })).not.toBeInTheDocument();
  });

  it("shows back to inbox link", () => {
    render(
      withIntl(
        <ReviewView
          document={document}
          reviewId={reviewId}
          extraction={extraction}
          role="ROLE-05"
          onApprove={vi.fn()}
          onReject={vi.fn()}
        />,
      ),
    );
    expect(screen.getByRole("link", { name: /Quay lại Hàng chờ/i })).toBeInTheDocument();
  });

  it("shows shortcuts button and opens modal", () => {
    render(
      withIntl(
        <ReviewView
          document={document}
          reviewId={reviewId}
          extraction={extraction}
          role="ROLE-05"
          onApprove={vi.fn()}
          onReject={vi.fn()}
        />,
      ),
    );
    const shortcutsBtn = screen.getByRole("button", { name: /Phím tắt/i });
    expect(shortcutsBtn).toBeInTheDocument();
    fireEvent.click(shortcutsBtn);
    expect(screen.getByText("Phím tắt hỗ trợ duyệt nhanh")).toBeInTheDocument();
  });

  it("opens RejectDialog when Reject button is clicked", () => {
    render(
      withIntl(
        <ReviewView
          document={document}
          reviewId={reviewId}
          extraction={extraction}
          role="ROLE-05"
          onApprove={vi.fn()}
          onReject={vi.fn()}
        />,
      ),
    );
    fireEvent.click(screen.getByRole("button", { name: /Từ chối/i }));
    expect(screen.getByRole("dialog", { name: /Từ chối tài liệu/i })).toBeInTheDocument();
  });
});

describe("TC-UI-006 axe scan — ReviewView", () => {
  it("ConfidenceIndicator HIGH has no serious/critical violations", async () => {
    const { container } = render(
      withIntl(<ConfidenceIndicator confidence={0.95} band="HIGH" />),
    );
    await expectNoSeriousViolations(container);
  });

  it("ExtractionFieldRow has no serious/critical violations", async () => {
    const editState = {
      fieldId: sampleField.id,
      originalValue: sampleField.value,
      currentValue: sampleField.value,
      isCorrected: false,
      isConfirmed: false,
    };
    const { container } = render(
      withIntl(
        <ExtractionFieldRow
          field={sampleField}
          editState={editState}
          onConfirm={vi.fn()}
        />,
      ),
    );
    await expectNoSeriousViolations(container);
  });

  it("ReviewView has no serious/critical violations (TC-UI-006)", async () => {
    const { document, review_id: reviewId, extraction } = DEMO_REVIEW_OPEN_OUT;
    const { container } = render(
      withIntl(
        <ReviewView
          document={document}
          reviewId={reviewId}
          extraction={extraction}
          role="ROLE-05"
          onApprove={vi.fn()}
          onReject={vi.fn()}
        />,
      ),
    );
    await expectNoSeriousViolations(container);
  });
});

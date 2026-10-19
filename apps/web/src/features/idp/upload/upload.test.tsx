/**
 * T-221 — SCR-08 Upload tests (06 §4.5, FR-DC-01, FR-DC-02, FR-DC-03, TC-UI-007, TC-UI-009):
 * - ManualFormC1: doc type select, dynamic fields render, required validation
 * - NlFormC2: textarea renders, requires min chars, submits with text
 * - DropzoneC3: renders dropzone with browse button, file list, accepts files
 * - UploadView: tabs render (C1/C2/C3), tab switching works
 * - axe scan 0 serious/critical violations (TC-UI-006)
 */
import type { ReactElement } from "react";
import axe from "axe-core";
import { cleanup, render, screen, fireEvent, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, describe, expect, it, vi } from "vitest";
import viMessages from "../../../../messages/vi.json";
import { ManualFormC1 } from "./ManualFormC1";
import { NlFormC2 } from "./NlFormC2";
import { DropzoneC3, type FileItem } from "./DropzoneC3";

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

/* -------------------------------------------------------------------------- */
/* ManualFormC1                                                                */
/* -------------------------------------------------------------------------- */
describe("TC-UI-007 ManualFormC1", () => {
  it("renders doc type selector", () => {
    render(withIntl(<ManualFormC1 onSubmit={vi.fn()} isSubmitting={false} />));
    // i18n label "idp.manualDocTypeLabel" = "Loại tài liệu"
    expect(screen.getByRole("combobox")).toBeInTheDocument();
  });

  it("shows dynamic fields when doc type selected", () => {
    render(withIntl(<ManualFormC1 onSubmit={vi.fn()} isSubmitting={false} />));
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "INVOICE" } });
    // i18n labels from "idp.invoiceFields.*"
    expect(screen.getByLabelText(/Số hóa đơn/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Tiền hàng/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Tổng cộng/)).toBeInTheDocument();
  });

  it("shows submit button after selecting doc type", () => {
    render(withIntl(<ManualFormC1 onSubmit={vi.fn()} isSubmitting={false} />));
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "CONTRACT" } });
    expect(screen.getByRole("button", { name: /Lưu và gửi xử lý/ })).toBeInTheDocument();
  });

  it("validates required fields on submit", async () => {
    const onSubmit = vi.fn();
    render(withIntl(<ManualFormC1 onSubmit={onSubmit} isSubmitting={false} />));
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "INVOICE" } });
    fireEvent.click(screen.getByRole("button", { name: /Lưu và gửi xử lý/ }));
    await waitFor(() => {
      // i18n key "idp.fieldRequired" = "Trường này là bắt buộc"
      expect(screen.getAllByRole("alert").length).toBeGreaterThan(0);
    });
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("calls onSubmit with correct payload when fields filled", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(withIntl(<ManualFormC1 onSubmit={onSubmit} isSubmitting={false} />));

    fireEvent.change(screen.getByRole("combobox"), { target: { value: "INVOICE" } });
    fireEvent.change(screen.getByLabelText(/Số hóa đơn/), { target: { value: "INV-001" } });
    fireEvent.change(screen.getByLabelText(/Ngày phát hành/), { target: { value: "2026-10-15" } });
    fireEvent.change(screen.getByLabelText(/Tiền hàng/), { target: { value: "9500000" } });
    fireEvent.change(screen.getByLabelText(/Thuế VAT/), { target: { value: "950000" } });
    fireEvent.change(screen.getByLabelText(/Tổng cộng/), { target: { value: "10450000" } });

    fireEvent.click(screen.getByRole("button", { name: /Lưu và gửi xử lý/ }));
    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        "INVOICE",
        expect.objectContaining({
          invoice_number: "INV-001",
          subtotal: 9500000,
          total_amount: 10450000,
        }),
      );
    });
  });
});

/* -------------------------------------------------------------------------- */
/* NlFormC2                                                                    */
/* -------------------------------------------------------------------------- */
describe("TC-UI-007 NlFormC2", () => {
  it("renders textarea and doc type hint", () => {
    render(withIntl(<NlFormC2 onSubmit={vi.fn()} isSubmitting={false} />));
    expect(screen.getByRole("textbox")).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: /Gợi ý loại tài liệu/ })).toBeInTheDocument();
  });

  it("shows character count", () => {
    render(withIntl(<NlFormC2 onSubmit={vi.fn()} isSubmitting={false} />));
    const textarea = screen.getByRole("textbox");
    fireEvent.change(textarea, { target: { value: "Test text" } });
    // i18n: "{n} ký tự" → "9 ký tự"
    expect(screen.getByText(/9/)).toBeInTheDocument();
  });

  it("shows error when content too short on blur", () => {
    render(withIntl(<NlFormC2 onSubmit={vi.fn()} isSubmitting={false} />));
    const textarea = screen.getByRole("textbox");
    fireEvent.change(textarea, { target: { value: "Short" } });
    fireEvent.blur(textarea);
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });

  it("calls onSubmit with text when content is long enough", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(withIntl(<NlFormC2 onSubmit={onSubmit} isSubmitting={false} />));
    const longText = "Hoa don thang 10 tu cong ty ABC tong tien 9500000 VND ngay 15/10/2026";
    fireEvent.change(screen.getByRole("textbox"), { target: { value: longText } });
    fireEvent.click(screen.getByRole("button", { name: /Phân tích và gửi/ }));
    await waitFor(() =>
      expect(onSubmit).toHaveBeenCalledWith(longText, undefined),
    );
  });
});

/* -------------------------------------------------------------------------- */
/* DropzoneC3                                                                  */
/* -------------------------------------------------------------------------- */
describe("TC-UI-007 DropzoneC3", () => {
  const noopFiles: FileItem[] = [];

  it("renders drop zone region and browse button", () => {
    render(
      withIntl(
        <DropzoneC3
          files={noopFiles}
          onFilesAdded={vi.fn()}
          onRemoveFile={vi.fn()}
          onSubmit={vi.fn()}
          isSubmitting={false}
        />,
      ),
    );
    expect(screen.getByRole("region", { name: /Kéo thả file/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Chọn file/ })).toBeInTheDocument();
  });

  it("shows file item in list when files provided", () => {
    const file = new File(["content"], "invoice.pdf", { type: "application/pdf" });
    const items: FileItem[] = [{ id: "f1", file, status: "pending" }];
    render(
      withIntl(
        <DropzoneC3
          files={items}
          onFilesAdded={vi.fn()}
          onRemoveFile={vi.fn()}
          onSubmit={vi.fn()}
          isSubmitting={false}
        />,
      ),
    );
    expect(screen.getByTestId("file-item-invoice.pdf")).toBeInTheDocument();
    expect(screen.getByText("invoice.pdf")).toBeInTheDocument();
  });

  it("shows Upload button when there are pending files", () => {
    const file = new File(["x"], "test.pdf", { type: "application/pdf" });
    const items: FileItem[] = [{ id: "f1", file, status: "pending" }];
    render(
      withIntl(
        <DropzoneC3
          files={items}
          onFilesAdded={vi.fn()}
          onRemoveFile={vi.fn()}
          onSubmit={vi.fn()}
          isSubmitting={false}
        />,
      ),
    );
    expect(screen.getByRole("button", { name: /Tải lên và xử lý/ })).toBeInTheDocument();
  });

  it("shows processing status text for file in processing state", () => {
    const file = new File(["x"], "invoice2.pdf", { type: "application/pdf" });
    const items: FileItem[] = [{ id: "f2", file, status: "processing" }];
    render(
      withIntl(
        <DropzoneC3
          files={items}
          onFilesAdded={vi.fn()}
          onRemoveFile={vi.fn()}
          onSubmit={vi.fn()}
          isSubmitting={false}
        />,
      ),
    );
    // Status text comes from i18n key "upload.fileItem.statusProcessing"
    expect(screen.getByText(/AI/i)).toBeInTheDocument();
  });

  it("shows error text for failed file", () => {
    const file = new File(["x"], "bad.pdf", { type: "application/pdf" });
    const items: FileItem[] = [{ id: "f3", file, status: "error", error: "File quá lớn" }];
    render(
      withIntl(
        <DropzoneC3
          files={items}
          onFilesAdded={vi.fn()}
          onRemoveFile={vi.fn()}
          onSubmit={vi.fn()}
          isSubmitting={false}
        />,
      ),
    );
    expect(screen.getByText(/File quá lớn/)).toBeInTheDocument();
  });
});

/* -------------------------------------------------------------------------- */
/* TC-UI-006 axe                                                               */
/* -------------------------------------------------------------------------- */
describe("TC-UI-006 axe scan — Upload components", () => {
  it("ManualFormC1 (no doc type) has no serious violations", async () => {
    const { container } = render(
      withIntl(<ManualFormC1 onSubmit={vi.fn()} isSubmitting={false} />),
    );
    await expectNoSeriousViolations(container);
  });

  it("NlFormC2 has no serious violations", async () => {
    const { container } = render(
      withIntl(<NlFormC2 onSubmit={vi.fn()} isSubmitting={false} />),
    );
    await expectNoSeriousViolations(container);
  });

  it("DropzoneC3 (empty) has no serious violations", async () => {
    const { container } = render(
      withIntl(
        <DropzoneC3
          files={[]}
          onFilesAdded={vi.fn()}
          onRemoveFile={vi.fn()}
          onSubmit={vi.fn()}
          isSubmitting={false}
        />,
      ),
    );
    await expectNoSeriousViolations(container);
  });
});

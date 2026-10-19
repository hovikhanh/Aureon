import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, screen, waitFor } from "@testing-library/react";
import type { DocumentSourceOut, ExtractedFieldOut } from "@aureon/shared-types";
import { ApiClientError } from "@/lib/api-client";
import { renderWithIntl } from "@/test/render";
import { SourceViewer } from "./SourceViewer";

const getDocumentSourceApi = vi.fn();
vi.mock("./source-api", () => ({
  getDocumentSourceApi: (...a: unknown[]) => getDocumentSourceApi(...a),
}));

function pageSource(): DocumentSourceOut {
  return {
    url: "https://minio.local/doc.pdf?sig=abc",
    expires_at: "2026-10-20T09:00:00Z",
    mime_type: "application/pdf",
    page_count: 1,
    pages: [
      { page_number: 1, image_url: "https://minio.local/p1.png", width_px: 1000, height_px: 1400, ocr_used: true, ocr_confidence: 0.9 },
    ],
    manual_info: null,
  };
}

const field = (over: Partial<ExtractedFieldOut> = {}): ExtractedFieldOut =>
  ({
    id: "f1",
    field_key: "invoice_number",
    table_key: null,
    row_index: null,
    record_group: null,
    value: "INV-001",
    raw_text: "INV-001",
    value_type: "text",
    confidence: 0.9,
    confidence_band: "HIGH",
    source_location: { kind: "BOUNDING_BOX", page: 1, x: 100, y: 200, w: 300, h: 40 },
    document_page_id: "p1",
    validation: [],
    sensitivity: "NONE",
    corrected: false,
    corrected_value: null,
    final_value: "INV-001",
    required: true,
    masked: false,
    ...over,
  }) as ExtractedFieldOut;

describe("SCR-10 SourceViewer (06 §4.7, EP-27, T-220)", () => {
  afterEach(() => {
    cleanup();
    getDocumentSourceApi.mockReset();
  });

  it("renders the page image and positions the highlight overlay for the selected field", async () => {
    getDocumentSourceApi.mockResolvedValue(pageSource());
    renderWithIntl(
      <SourceViewer
        documentId="doc-1"
        channel="C3"
        fields={[field()]}
        selectedFieldId="f1"
        token="tok"
      />,
    );
    const img = await screen.findByRole("img");
    expect(img).toHaveAttribute("src", "https://minio.local/p1.png");
    const overlay = await screen.findByLabelText(/Vùng chứa giá trị/i);
    // x/width_px = 100/1000 = 10%, w/width_px = 300/1000 = 30%
    expect(overlay).toHaveStyle({ left: "10%", width: "30%" });
  });

  it("shows the manual-entry panel for a virtual C1 document (no file)", async () => {
    getDocumentSourceApi.mockResolvedValue({
      url: null,
      expires_at: null,
      mime_type: null,
      page_count: null,
      pages: [],
      manual_info: { created_by_full_name: "Nguyễn Văn An", created_at: "2026-10-05T08:30:00Z" },
    } satisfies DocumentSourceOut);
    renderWithIntl(<SourceViewer documentId="doc-c1" channel="C1" token="tok" />);
    await waitFor(() => expect(screen.getByText(/Nhập tay bởi/i)).toBeInTheDocument());
  });

  it("shows the salary-forbidden state on 403 FORBIDDEN_SALARY", async () => {
    getDocumentSourceApi.mockRejectedValue(
      new ApiClientError("FORBIDDEN_SALARY", "no", 403),
    );
    renderWithIntl(<SourceViewer documentId="doc-hr" channel="C3" token="tok" />);
    await waitFor(() =>
      expect(screen.getByText(/chỉ Trưởng phòng nhân sự được mở/i)).toBeInTheDocument(),
    );
  });

  it("hides the download button unless the role may download", async () => {
    getDocumentSourceApi.mockResolvedValue(pageSource());
    renderWithIntl(<SourceViewer documentId="doc-1" channel="C3" token="tok" />);
    await screen.findByRole("img");
    expect(screen.queryByText(/Tải xuống/i)).not.toBeInTheDocument();
  });
});

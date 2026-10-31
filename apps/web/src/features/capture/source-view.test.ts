/**
 * R-DEC-80 — "Xem tài liệu gốc" view-state logic (EP-DC-14 → EP-DC-14b). Verifies the drawer
 * frames a servable original, falls back to the text layer, and — the core of the fix —
 * distinguishes a 403 / load error from "no text", so a permission error is never shown as
 * "no text layer". TC-SRC-FE-01..06.
 */
import { describe, expect, it } from "vitest";
import { ApiError } from "@/lib/api-client";
import type { SourceView } from "./types";
import { servable, sourceViewState } from "./source-view";

const view = (over: Partial<SourceView> = {}): SourceView => ({
  url: "/api/backend/files/documents/abc?expires=1&signature=s",
  mime_type: "application/pdf",
  page_count: 2,
  page: 1,
  filename: "q3.pdf",
  pages: [
    { page_number: 1, text_content: "trang 1 nội dung" },
    { page_number: 2, text_content: "trang 2 nội dung" },
  ],
  ...over,
});

describe("servable", () => {
  it("accepts the BFF file path, absolute and data URLs; rejects bare relative paths", () => {
    expect(servable("/api/backend/files/documents/x?expires=1&signature=s")).toBe(true);
    expect(servable("https://minio.local/b/x")).toBe(true);
    expect(servable("data:image/png;base64,AAAA")).toBe(true);
    expect(servable("/files/documents/x")).toBe(false);
    expect(servable("")).toBe(false);
  });
});

describe("sourceViewState", () => {
  it("frames the original when the URL is servable (TC-SRC-FE-01)", () => {
    expect(sourceViewState(view(), 1)).toEqual({ kind: "frame", url: view().url });
  });

  it("frames an image original too", () => {
    const img = view({ url: "data:image/png;base64,AAAA", mime_type: "image/png" });
    expect(sourceViewState(img, 1).kind).toBe("frame");
  });

  it("falls back to the text layer when the URL is not servable (TC-SRC-FE-02)", () => {
    const s = sourceViewState(view({ url: "/files/documents/x" }), 2);
    expect(s).toEqual({ kind: "text", text: "trang 2 nội dung" });
  });

  it("falls back to the text layer when the iframe failed to load", () => {
    const s = sourceViewState(view(), 1, { frameFailed: true });
    expect(s).toEqual({ kind: "text", text: "trang 1 nội dung" });
  });

  it("'no text layer' when the document has no pages, distinct from an error (TC-SRC-FE-03)", () => {
    const s = sourceViewState(view({ url: "/files/x", pages: null }), 1);
    expect(s).toEqual({ kind: "no-text-layer" });
  });

  it("'page no text' when this page is empty but others have text (TC-SRC-FE-04)", () => {
    const v = view({ url: "/files/x", pages: [{ page_number: 1, text_content: null }, { page_number: 2, text_content: "x" }] });
    expect(sourceViewState(v, 1)).toEqual({ kind: "page-no-text" });
  });

  it("a 403 is 'forbidden', NOT 'no text layer' — the original bug (TC-SRC-FE-05)", () => {
    const err = new ApiError(403, "FORBIDDEN_SCOPE", "invalid or expired signature", { reason: "signature" });
    expect(sourceViewState(view(), 1, { error: err })).toEqual({ kind: "forbidden" });
    // even when pages[] is present (has text), a 403 must not be masked as "no text"
    expect(sourceViewState(view(), 1, { error: err }).kind).not.toBe("no-text-layer");
  });

  it("a non-403 load error surfaces as a generic error (TC-SRC-FE-06)", () => {
    const err = new ApiError(404, "NOT_FOUND", "file not found");
    expect(sourceViewState(view(), 1, { error: err })).toEqual({ kind: "error" });
    // undefined data with no error is also an error, not a silent empty state
    expect(sourceViewState(undefined, 1)).toEqual({ kind: "error" });
  });
});

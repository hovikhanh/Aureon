/**
 * Pure decision logic for "Xem tài liệu gốc" (EP-DC-14 → EP-DC-14b, R-DEC-80), split out of
 * `SourceDrawer.tsx` so it is unit-testable in the node test environment (no DOM). Decides
 * whether to frame the original file, show the extracted text layer, or surface an error —
 * and critically distinguishes a permission/expiry error from "there is simply no text".
 */
import { ApiError } from "@/lib/api-client";
import type { SourceView } from "./types";

/** R-DEC-80: the presigned URL now routes through the BFF (`/api/backend/files/...`), so the
 * browser can frame it; absolute http(s) / data: URLs (MinIO/S3 presign) work too. Anything
 * else (e.g. a MANUAL doc with no file) is not frameable → text-layer fallback. */
export const servable = (url: string): boolean => /^(https?:|data:|\/api\/backend\/)/i.test(url);

export type SourceState =
  | { kind: "frame"; url: string }
  | { kind: "text"; text: string }
  | { kind: "no-text-layer" } // the document has no extracted pages at all
  | { kind: "page-no-text" } //  this page carries no text
  | { kind: "forbidden" } //     403 — signature/scope, NOT "no text"
  | { kind: "error" }; //        any other load failure

/**
 * Resolve what the drawer should render for `page`.
 * - a load error is classified first: 403 → `forbidden` (read not permitted / link expired),
 *   anything else → `error`. It is never collapsed into "no text layer" (the original bug).
 * - with data: frame the file when its URL is servable and the frame has not failed;
 *   otherwise fall back to the extracted text layer, distinguishing the empty cases.
 */
export function sourceViewState(
  view: SourceView | undefined,
  page: number,
  opts: { error?: unknown; frameFailed?: boolean } = {},
): SourceState {
  if (opts.error) {
    if (opts.error instanceof ApiError && opts.error.status === 403) return { kind: "forbidden" };
    return { kind: "error" };
  }
  if (!view) return { kind: "error" };
  if (servable(view.url) && !opts.frameFailed) return { kind: "frame", url: view.url };
  if (!view.pages || view.pages.length === 0) return { kind: "no-text-layer" };
  const p = view.pages.find((x) => x.page_number === page);
  if (!p?.text_content) return { kind: "page-no-text" };
  return { kind: "text", text: p.text_content };
}

/** TC-M15-16 (FE unit) — UndoToast timer + EP-DC-24 call, LineageChip states (restricted), capture error mapping. */
import { afterEach, describe, expect, it, vi } from "vitest";
import { createUndoTimer, UNDO_TOAST_MS } from "@/components/ai/undo-timer";
import { ApiError } from "@/lib/api-client";
import { captureError, ruleMessage } from "./errors";
import { lineageView, linkLocation } from "./lineage-view";
import { undoDocument } from "./use-capture";
import type { LineageLink } from "./types";
import vi_ from "../../../messages/vi.json";

function fakeTimers() {
  let now = 0;
  const jobs = new Map<number, { at: number; fn: () => void }>();
  let seq = 0;
  return {
    timers: { now: () => now, set: (fn: () => void, ms: number) => { jobs.set(++seq, { at: now + ms, fn }); return seq; }, clear: (h: unknown) => void jobs.delete(h as number) },
    tick(ms: number) { now += ms; for (const [k, j] of [...jobs]) if (j.at <= now) { jobs.delete(k); j.fn(); } },
  };
}

describe("UndoToast timer (06 §5.1)", () => {
  it("expires after 10 s; hover/focus pause and resume with the remaining time", () => {
    const f = fakeTimers();
    const expire = vi.fn();
    const timer = createUndoTimer(expire, UNDO_TOAST_MS, f.timers);
    timer.start();
    f.tick(4000);
    timer.pause("hover");
    timer.pause("focus");
    f.tick(60_000);
    expect(expire).not.toHaveBeenCalled();
    timer.resume("hover");
    f.tick(60_000);
    expect(expire).not.toHaveBeenCalled();
    expect(timer.remaining()).toBe(6000);
    timer.resume("focus");
    f.tick(5999);
    expect(expire).not.toHaveBeenCalled();
    f.tick(1);
    expect(expire).toHaveBeenCalledTimes(1);
    expect(timer.done).toBe(true);
  });

  it("cancel stops the countdown", () => {
    const f = fakeTimers();
    const expire = vi.fn();
    const timer = createUndoTimer(expire, UNDO_TOAST_MS, f.timers);
    timer.start();
    timer.cancel();
    f.tick(20_000);
    expect(expire).not.toHaveBeenCalled();
  });
});

describe("Undo action → EP-DC-24", () => {
  afterEach(() => vi.unstubAllGlobals());
  it("POSTs reason + reason_code with an Idempotency-Key", async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ data: { document: { id: "d1", status: "ROLLED_BACK" }, reverted_actions: [] } }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const out = await undoDocument("d1", "Nhập nhầm", "mistake");
    expect(out.document.status).toBe("ROLLED_BACK");
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/api/backend/data-capture/documents/d1/undo");
    expect(init.method).toBe("POST");
    expect((init.headers as Record<string, string>)["idempotency-key"]).toBeTruthy();
    expect(JSON.parse(String(init.body))).toEqual({ reason: "Nhập nhầm", reason_code: "mistake" });
  });
});

const link = (o: Partial<LineageLink>): LineageLink => ({ target_column: "code", source_document_id: "d1", document_type: "HR_ROSTER", original_filename: "DOC-06.xlsx", page_number: null, sheet_name: "Nhân sự",
  row_index: 2, field_name: "employee_code", raw_text: "NV-001", confidence: 0.97, action_name: "ACT-create_employee", committed_at: "2026-10-24T01:00:00Z", revoked_at: null, ...o });

describe("LineageChip view (EP-DC-26)", () => {
  it("restricted never exposes links; empty → none", () => {
    expect(lineageView({ restricted: true, reason: "target_out_of_scope" })).toEqual({ kind: "restricted" });
    expect(lineageView({ entity: "hr.employees", id: "x", links: [], restricted: false, reason: null })).toEqual({ kind: "none" });
    expect(lineageView(undefined)).toEqual({ kind: "none" });
  });
  it("groups by document; revoked documents last; location parts", () => {
    const v = lineageView({ restricted: false, links: [link({ source_document_id: "old", revoked_at: "2026-10-23T00:00:00Z", committed_at: "2026-10-22T00:00:00Z" }), link({}), link({ field_name: "full_name" })] });
    expect(v.kind === "links" && v.documents.map((d) => [d.source_document_id, d.links.length, d.revoked])).toEqual([["d1", 2, false], ["old", 1, true]]);
    expect(linkLocation(link({}))).toEqual({ sheet: "Nhân sự", row: 2 });
    expect(linkLocation(link({ sheet_name: null, row_index: null, page_number: 3 }))).toEqual({ page: 3 });
  });
});

describe("capture error messages", () => {
  const dict = vi_ as unknown as Record<string, Record<string, Record<string, string>>>;
  const lookup = (k: string) => k.split(".").reduce<unknown>((o, p) => (o as Record<string, unknown> | undefined)?.[p], dict);
  const t = Object.assign((k: string, v: Record<string, string | number> = {}) => String(lookup(k)).replace(/\{(\w+)\}/g, (_, n: string) => String(v[n] ?? "")), { has: (k: string) => typeof lookup(k) === "string" });
  it("413 by details.limit, 422 by details.reason, rule codes, unknown fallback", () => {
    expect(captureError(t, new ApiError(413, "FILE_TOO_LARGE", "", { limit: "rows" }))).toBe("File vượt 5.000 dòng");
    expect(captureError(t, new ApiError(422, "BUSINESS_RULE_VIOLATION", "", { reason: "no_file" }))).toBe("Tài liệu nhập tay không có file gốc");
    expect(captureError(t, new ApiError(403, "FORBIDDEN_ROLE", "", { missing: ["hr:admin"] }))).toBe("Thiếu quyền ghi: hr:admin");
    expect(captureError(t, new ApiError(410, "UNDO_EXPIRED", ""))).toBe("Đã quá hạn hoàn tác 7 ngày");
    expect(ruleMessage(t, "master_not_found", { value: "ADMIN" })).toBe("Không tìm thấy mã \"ADMIN\" trong danh mục");
    expect(ruleMessage(t, "weird_rule")).toBe("Lỗi kiểm tra (weird_rule)");
  });
});

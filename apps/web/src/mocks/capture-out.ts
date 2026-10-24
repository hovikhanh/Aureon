/** Mock D03 DTO mappers + shared request helpers (DocumentOut / InboxItemOut / ReviewFieldOut …). */
import type { MockClaims } from "./fixtures";
import { MockHttpError } from "./http";
import type { MockRequest } from "./router";
import { canPerm, seesLevel4 } from "./capture-scope";
import { addDays, captureStore, nowIso, UNDO_DAYS, type MDoc, type MField } from "./capture-store";
import { actionRefs, commitDoc } from "./capture-actions";
import { recordAudit } from "./audit";

export const err = (status: number, code: string, message: string, details: Record<string, unknown> = {}) => new MockHttpError(status, code, message, details);
export const body = (req: MockRequest): Record<string, unknown> => (req.body && typeof req.body === "object" ? (req.body as Record<string, unknown>) : {});
export function requireIdem(req: MockRequest): void {
  if (!req.headers.get("idempotency-key")?.trim()) throw err(400, "BAD_REQUEST", "Idempotency-Key header is required", { header: "Idempotency-Key" });
}
export function expectVersion(req: MockRequest, current: number): void {
  const v = body(req).version;
  if (typeof v !== "number") throw err(422, "VALIDATION_ERROR", "version is required", { field: "version" });
  if (v !== current) throw err(409, "CONFLICT_STATE", "stale version", { expected: current });
}

export function undoable(c: MockClaims, d: MDoc): boolean {
  if (d.status !== "COMMITTED" || !d.undo_deadline || d.undo_deadline <= nowIso() || !c.permissions.includes("idp:write")) return false;
  const mine = d.submitted_by === c.sub || d.approved_by === c.sub;
  const allDepts = c.role === "CEO" || (c.role === "DIR" && (c.scope_pillars.length === 0 || d.pillars.some((p) => c.scope_pillars.includes(p))));
  if (!mine && !(allDepts && c.role !== "REV")) return false;
  // every ACT to revert must be permitted (R-DEC-66)
  return d.actions.every((a) => a.status !== "applied" || needs(a.action_name).some((p) => canPerm(c, p) || (c.role === "EMP" && a.action_name === "ACT-create_task")));
}
const needs = (a: string) => (a === "ACT-create_employee" ? ["hr:write", "hr:admin"] : a.startsWith("ACT-create_department") ? ["hr:admin"] : a === "ACT-create_invoice" ? ["finance:write"] : ["execution:write"]);

export function docOut(c: MockClaims, d: MDoc) {
  return {
    id: d.id, version: d.version, original_filename: d.original_filename, mime_type: d.mime_type, size_bytes: d.size_bytes, page_count: d.page_count, channel: d.channel,
    kind: d.kind, status: d.status, status_reason: d.status_reason, scan_status: "CLEAN", pillars: d.pillars, sensitivity_level: d.sensitivity_level, submitted_at: d.submitted_at,
    document_type: d.document_type, committed_at: d.committed_at, undo_deadline: d.undo_deadline, can_undo: undoable(c, d), rolled_back_at: d.rolled_back_at,
  };
}

export function recordCount(d: MDoc): number | null {
  if (!["COMMITTED", "AUTO_APPROVED", "ROLLED_BACK"].includes(d.status)) return null;
  return d.actions.reduce((n, a) => n + a.result_refs.filter((r) => !r.reused).length, 0);
}

export function inboxOut(c: MockClaims, d: MDoc) {
  return { document: docOut(c, d), document_type: d.document_type, channel: d.channel, submitted_by_name: d.submitted_by_name, record_count: recordCount(d),
    undo_deadline: d.undo_deadline, can_undo: undoable(c, d), batch_id: d.batch_id };
}

const band = (x: number) => (x >= 0.9 ? "HIGH" : x >= 0.6 ? "MEDIUM" : "LOW");
export const mask = (c: MockClaims, d: MDoc, level: number, v: unknown) => (level >= 4 && !seesLevel4(c, d) && v !== null ? { masked: true } : v);
export function fieldOut(c: MockClaims, d: MDoc, f: MField) {
  const eff = f.corrected_value !== null && f.corrected_value !== undefined ? f.corrected_value : f.ai_value;
  return { id: f.id, field_name: f.field_name, row_index: f.row_index, value_type: f.value_type, ai_value: mask(c, d, f.sensitivity_level, f.ai_value),
    corrected_value: mask(c, d, f.sensitivity_level, f.corrected_value), effective_value: mask(c, d, f.sensitivity_level, eff), confidence: f.confidence, confidence_band: band(f.confidence),
    is_critical: f.is_critical, is_confirmed: f.is_confirmed, source_location: f.source_location, validation: f.validation, correction_reason: f.correction_reason };
}

export function findDoc(id: string | undefined): MDoc {
  const d = captureStore().docs.find((x) => x.id === id);
  if (!d) throw err(404, "NOT_FOUND", "document not found");
  return d;
}

/** Commit + bookkeeping shared by approve (EP-DC-08), manual (16) and commit (23). */
export function finishCommit(req: MockRequest, d: MDoc) {
  const acts = commitDoc(req.claims, d);
  const at = nowIso();
  Object.assign(d, { status: "COMMITTED", committed_at: at, undo_deadline: addDays(at, UNDO_DAYS), approved_by: d.approved_by ?? req.claims.sub, version: d.version + 1, locked_by: null, locked_until: null });
  recordAudit(req.claims, "idp.document.committed", "source_documents", d.id);
  return { document: docOut(req.claims, d), actions: actionRefs(acts), undo_deadline: d.undo_deadline };
}


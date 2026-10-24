/**
 * Mock IDP review EP-DC-01..10 (M1.5 shape): upload (multipart parsed by the BFF into
 * `{files:[{name,size,type}], document_type}`), document by id, review queue, review detail with
 * `rows` / `planned_actions` / `can_commit`, soft lock, field edits, approve (COMMITTED vs
 * APPROVED + `meta.pending_permissions`, 422 critical_unconfirmed), reject, release.
 */
import { ok } from "./http";
import { recordAudit } from "./audit";
import type { MockRequest, Route } from "./router";
import { plannedActions } from "./capture-actions";
import { docVisible, reviewVisible } from "./capture-scope";
import { captureStore, newCaptureId, nowIso, type MDoc } from "./capture-store";
import { docBase } from "./capture-seed";
import { body, docOut, err, fieldOut, findDoc, finishCommit, requireIdem } from "./capture-out";

const OPEN = ["NEEDS_REVIEW", "IN_REVIEW", "APPROVED"];
const ACCEPT = /\.(pdf|png|jpe?g|webp|heic|docx|xlsx|csv)$/i;

function upload(req: MockRequest): Response {
  requireIdem(req);
  const b = body(req);
  const files = (Array.isArray(b.files) ? b.files : []) as { name: string; size: number; type: string }[];
  if (files.length < 1 || files.length > 100) throw err(422, "VALIDATION_ERROR", "1..100 files", { field: "files" });
  const type = b.document_type ? String(b.document_type) : null;
  if (type && !captureStore().docTypes.some((t) => t.code === type && t.is_active)) throw err(422, "VALIDATION_ERROR", "unknown document_type", { field: "document_type" });
  for (const f of files) {
    if (!ACCEPT.test(f.name) || f.name.toLowerCase().endsWith(".xls")) throw err(415, "UNSUPPORTED_MEDIA_TYPE", "file type not allowed", { filename: f.name });
    if (f.size > 50 * 1024 * 1024) throw err(413, "FILE_TOO_LARGE", "file exceeds 50 MB", { filename: f.name, limit: "size" });
  }
  const batch = files.length > 1 ? newCaptureId("batch") : null;
  const docs = files.map((f) => docBase({ id: newCaptureId("document"), submitter: req.claims.email, submitted_by_name: req.claims.name, original_filename: f.name, mime_type: f.type || null,
    size_bytes: f.size, page_count: 1, channel: "C3", status: "UPLOADED", document_type: type, submitted_at: nowIso(), batch_id: batch }));
  captureStore().docs.push(...docs);
  recordAudit(req.claims, "idp.upload", "source_documents", docs[0]!.id);
  return ok({ document_ids: docs.map((d) => d.id), job_ids: docs.map(() => newCaptureId("job")), batch_id: batch, duplicates: [] }, 202);
}

function visible(req: MockRequest, review = false): MDoc {
  const d = findDoc(req.params.id);
  if (!(review ? reviewVisible(req.claims, d) : docVisible(req.claims, d))) throw err(404, "NOT_FOUND", "document not found");
  return d;
}

function queue(req: MockRequest): Response {
  const q = req.query;
  const st = q.get("status");
  const type = q.get("document_type");
  const who = q.get("assigned_to");
  const rows = captureStore().docs.filter((d) => OPEN.includes(d.status) && reviewVisible(req.claims, d) && (!st || d.status === st) && (!type || d.document_type === type) && (!who || d.assigned_to === who));
  const limit = Math.min(Number(q.get("limit") ?? 20) || 20, 100);
  const offset = Number(q.get("offset") ?? 0) || 0;
  const data = rows.slice(offset, offset + limit).map((d) => ({ document_id: d.id, filename: d.original_filename, document_type: d.document_type, status: d.status,
    confidence_avg: d.document_confidence, critical_fields_count: d.fields.filter((f) => f.is_critical).length, validation_error_count: 0, routing_reason: d.routing_reasons[0] ?? null,
    age_hours: (Date.now() - Date.parse(d.submitted_at)) / 3_600_000, assigned_to: d.assigned_to, due_at: null, locked_by: d.locked_by, locked_until: d.locked_until }));
  return ok(data, 200, { pagination: { total: rows.length, limit, offset, has_next: offset + data.length < rows.length } });
}

export function reviewOut(req: MockRequest, d: MDoc) {
  const c = req.claims;
  const fields = d.fields.map((f) => fieldOut(c, d, f));
  const idx = [...new Set(d.fields.flatMap((f) => (f.row_index === null ? [] : [f.row_index])))].sort((a, b) => a - b);
  const planned = d.status === "ROLLED_BACK" ? [] : plannedActions(c, d);
  return { document: docOut(c, d), job_id: null, pages: d.kind === "MANUAL" ? [] : [{ id: `${d.id}-p1`, page_number: 1, sheet_name: d.sheet_name, text_layer_exists: true, ocr_used: false, ocr_confidence: null, text_content: d.original_filename }],
    fields, validation_errors: [], document_confidence: d.document_confidence, routing_decision: "REVIEW", routing_reasons: d.routing_reasons, assigned_to: d.assigned_to,
    locked_by: d.locked_by, locked_until: d.locked_until, rows: idx.map((i) => ({ row_index: i, fields: fields.filter((f) => f.row_index === i) })), planned_actions: planned,
    can_commit: d.status === "APPROVED" && planned.length > 0 && planned.every((p) => p.permitted) && c.permissions.includes("idp:write") };
}

function open(req: MockRequest): Response {
  requireIdem(req);
  const d = visible(req, true);
  if (d.locked_by && d.locked_by !== req.claims.sub && d.locked_until && d.locked_until > nowIso()) throw err(409, "REVIEW_LOCKED", "locked by another reviewer", { locked_by: d.locked_by, locked_until: d.locked_until });
  const until = new Date(Date.now() + 15 * 60_000).toISOString();
  Object.assign(d, { locked_by: req.claims.sub, locked_until: until, status: d.status === "NEEDS_REVIEW" ? "IN_REVIEW" : d.status });
  return ok({ locked_until: until, document: docOut(req.claims, d) });
}

function patchFields(req: MockRequest): Response {
  const d = visible(req, true);
  const edits = (Array.isArray(body(req).fields) ? body(req).fields : []) as { field_id: string; action?: string; value?: unknown; reason?: string | null }[];
  for (const e of edits) {
    const f = d.fields.find((x) => x.id === e.field_id);
    if (!f) throw err(422, "VALIDATION_ERROR", "unknown field_id", { field: "field_id" });
    if (e.action === "clear") Object.assign(f, { corrected_value: null, is_confirmed: true });
    else if (e.action === "confirm") f.is_confirmed = true;
    else Object.assign(f, { corrected_value: e.value, is_confirmed: true, correction_reason: e.reason ?? null });
  }
  if (body(req).accept_all_high) for (const f of d.fields) if (!f.is_critical && f.confidence >= 0.9) f.is_confirmed = true;
  return ok({ fields: d.fields.map((f) => fieldOut(req.claims, d, f)), validation_errors: [], validations_ok: true });
}

function approve(req: MockRequest): Response {
  requireIdem(req);
  const d = visible(req, true);
  if (!["NEEDS_REVIEW", "IN_REVIEW"].includes(d.status)) throw err(409, "CONFLICT_STATE", "document is not in review", { status: d.status });
  const v = body(req).version;
  if (typeof v === "number" && v !== d.version) throw err(409, "CONFLICT_STATE", "stale version", { expected: d.version });
  const pending = d.fields.filter((f) => f.is_critical && !f.is_confirmed);
  if (pending.length) throw err(422, "ACTION_REJECTED", "critical fields not confirmed", { reason: "critical_unconfirmed", fields: [...new Set(pending.map((f) => f.field_name))].sort() });
  const planned = plannedActions(req.claims, d);
  d.approved_by = req.claims.sub;
  if (planned.every((p) => p.permitted) && req.claims.permissions.includes("idp:write")) return ok(finishCommit(req, d));
  Object.assign(d, { status: "APPROVED", version: d.version + 1, locked_by: null, locked_until: null });
  recordAudit(req.claims, "idp.document_approve", "source_documents", d.id);
  return ok({ document: docOut(req.claims, d), actions: [], undo_deadline: null }, 200, { pending_permissions: [...new Set(planned.filter((p) => !p.permitted).map((p) => p.required_permission))] });
}

function reject(req: MockRequest): Response {
  requireIdem(req);
  const d = visible(req, true);
  const reason = body(req).reason;
  if (typeof reason !== "string" || !reason.trim()) throw err(422, "VALIDATION_ERROR", "reason is required", { field: "reason" });
  Object.assign(d, { status: "REJECTED", status_reason: reason, version: d.version + 1, locked_by: null, locked_until: null });
  return ok(docOut(req.claims, d));
}

function release(req: MockRequest): Response {
  const d = visible(req, true);
  if (d.locked_by === req.claims.sub) Object.assign(d, { locked_by: null, locked_until: null });
  return ok(docOut(req.claims, d));
}

export const CAPTURE_REVIEW_ROUTES: readonly Route[] = [
  { method: "POST", pattern: "/idp/documents", permission: "idp:write", handler: upload },
  { method: "GET", pattern: "/idp/documents/:id", permission: "idp:read", handler: (req) => ok(docOut(req.claims, visible(req))) },
  { method: "GET", pattern: "/idp/review-queue", permission: "idp:approve", handler: queue },
  { method: "GET", pattern: "/idp/documents/:id/review", permission: "idp:approve", handler: (req) => ok(reviewOut(req, visible(req, true))) },
  { method: "POST", pattern: "/idp/documents/:id/review/open", permission: "idp:approve", handler: open },
  { method: "PATCH", pattern: "/idp/documents/:id/fields", permission: "idp:approve", handler: patchFields },
  { method: "POST", pattern: "/idp/documents/:id/review/approve", permission: "idp:approve", handler: approve },
  { method: "POST", pattern: "/idp/documents/:id/review/reject", permission: "idp:approve", handler: reject },
  { method: "POST", pattern: "/idp/documents/:id/review/release", permission: "idp:approve", handler: release },
];

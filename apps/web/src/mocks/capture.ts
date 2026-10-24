/**
 * Mock BFF D03 Data Capture (M1.5, EP-DC-13..16, 23..26) on `API_MODE=mock`. Contract = 10 §7.2.4:
 * inbox groups + `meta.counts`, scope per role (ADM scope `s`: own #4 HR_ROSTER, R-DEC-76), source view (MANUAL → 422),
 * C1 form/manual submit (commit now when the caller holds every target permission, else
 * NEEDS_REVIEW), commit of APPROVED docs, 7-day undo (410 / 409 conflicts), lineage
 * (`restricted` out of scope). Review EP-DC-04..10 live in `capture-review.ts`, C5 in
 * `capture-import.ts`, admin in `capture-admin.ts`.
 */
import { ok, parsePage } from "./http";
import { recordAudit } from "./audit";
import type { MockRequest, Route } from "./router";
import { validateValues, type RowError } from "./capture-rules";
import { lineage } from "./capture-lineage";
import { actPermitted, docVisible, seesLevel4 } from "./capture-scope";
import { actionRefs, plannedActions, undoDoc } from "./capture-actions";
import { captureStore, GROUPS, groupOf, newCaptureId, nowIso, REVIEWER, userId, type MDoc } from "./capture-store";
import { docBase, makeFields } from "./capture-seed";
import { body, docOut, err, expectVersion, findDoc, finishCommit, inboxOut, requireIdem, undoable } from "./capture-out";
import { CAPTURE_IMPORT_ROUTES } from "./capture-import";
import { CAPTURE_REVIEW_ROUTES } from "./capture-review";
import { CAPTURE_ADMIN_ROUTES } from "./capture-admin";

function inbox(req: MockRequest): Response {
  const c = req.claims;
  if (!c.permissions.includes("idp:read")) throw err(403, "FORBIDDEN_ROLE", "inbox not available for this role", { role: c.role });
  const q = req.query;
  const group = q.get("group");
  if (group && !GROUPS[group]) throw err(422, "VALIDATION_ERROR", "unknown group", { field: "group" });
  const [ch, type, mine, text, from, to] = ["channel", "document_type", "mine", "q", "date_from", "date_to"].map((k) => q.get(k) ?? "");
  const scoped = captureStore().docs.filter((d) => docVisible(c, d) && (!["EMP", "ADM"].includes(c.role) || d.submitted_by === c.sub) && (c.role !== "ADM" || d.document_type === "HR_ROSTER")).filter((d) =>
    (!ch || d.channel === ch) && (!type || d.document_type === type) && (mine !== "true" || d.submitted_by === c.sub)
    && (!text || (d.original_filename ?? "").toLowerCase().includes(text!.toLowerCase())) && (!from || d.submitted_at.slice(0, 10) >= from!) && (!to || d.submitted_at.slice(0, 10) <= to!));
  const counts = Object.fromEntries(Object.keys(GROUPS).map((g) => [g, scoped.filter((d) => groupOf(d.status) === g).length]));
  const page = parsePage(q, ["submitted_at", "committed_at"]);
  const key = (page.sortBy ?? "submitted_at") as "submitted_at" | "committed_at";
  const order = page.sortBy ? page.order : "desc";
  const rows = scoped.filter((d) => !group || groupOf(d.status) === group)
    .sort((a, b) => (a[key] ?? "").localeCompare(b[key] ?? "") * (order === "desc" ? -1 : 1));
  const data = rows.slice(page.offset, page.offset + page.limit).map((d) => inboxOut(c, d));
  return ok(data, 200, { pagination: { total: rows.length, limit: page.limit, offset: page.offset, has_next: page.offset + data.length < rows.length }, counts });
}

function visibleDoc(req: MockRequest): MDoc {
  const d = findDoc(req.params.id);
  if (!docVisible(req.claims, d)) throw err(404, "NOT_FOUND", "document not found");
  return d;
}

function source(req: MockRequest): Response {
  const d = visibleDoc(req);
  if (d.kind === "MANUAL") throw err(422, "BUSINESS_RULE_VIOLATION", "manual document has no file", { reason: "no_file" });
  const page = Number(req.query.get("page") ?? 1);
  if (d.sensitivity_level >= 3) recordAudit(req.claims, "idp.source_view", "source_documents", d.id);
  // Mock-only presigned URL: an inline SVG "page" (no object storage in mock mode); keeps the document id for tests.
  const esc = (x: string) => x.replace(/[&<>"]/g, "_");
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="595" height="842"><rect width="100%" height="100%" fill="white"/><text x="40" y="60" font-size="18">${esc(d.original_filename ?? "")}</text><text x="40" y="90" font-size="14">p. ${page} · ${d.id}</text></svg>`;
  return ok({ url: `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`, mime_type: d.mime_type, page_count: d.page_count, page });
}

function actions(req: MockRequest): Response {
  const d = visibleDoc(req);
  return ok(d.actions.map((a) => ({ ...a, result_refs: a.result_refs.map((r) => ({ schema: r.schema, table: r.table, id: r.id, reused: r.reused })) })));
}

function commit(req: MockRequest): Response {
  requireIdem(req);
  const d = visibleDoc(req);
  if (d.status !== "APPROVED") throw err(409, "CONFLICT_STATE", "document is not APPROVED", { status: d.status });
  expectVersion(req, d.version);
  const missing = plannedActions(req.claims, d).filter((p) => !p.permitted).map((p) => p.required_permission);
  if (missing.length) throw err(403, "FORBIDDEN_ROLE", "missing target permission", { missing: [...new Set(missing)] });
  return ok(finishCommit(req, d));
}

const REASONS = ["mistake", "critical_field_wrong", "duplicate", "other"];
function undo(req: MockRequest): Response {
  requireIdem(req);
  const c = req.claims;
  const d = visibleDoc(req);
  const b = body(req);
  if (typeof b.reason !== "string" || !b.reason.trim()) throw err(422, "VALIDATION_ERROR", "reason is required", { field: "reason" });
  if (!REASONS.includes(String(b.reason_code))) throw err(422, "VALIDATION_ERROR", "invalid reason_code", { field: "reason_code" });
  if (d.status !== "COMMITTED") throw err(409, "CONFLICT_STATE", "document is not COMMITTED", { status: d.status });
  if (!d.undo_deadline || d.undo_deadline <= nowIso()) throw err(410, "UNDO_EXPIRED", "undo window expired", { undo_deadline: d.undo_deadline });
  if (!undoable(c, d)) throw err(403, "FORBIDDEN_ROLE", "not allowed to undo this document");
  const reverted = undoDoc(d);
  Object.assign(d, { status: "ROLLED_BACK", rolled_back_at: nowIso(), version: d.version + 1 });
  if (b.reason_code === "critical_field_wrong") {
    const f = d.fields.find((x) => x.is_critical);
    captureStore().incidents.push({ id: newCaptureId("incident"), source_document_id: d.id, extracted_field_id: f?.id ?? null, field_name: f?.field_name ?? "unknown", is_critical: true,
      detected_by: "undo", undetected: true, target_table: null, target_id: null, description: String(b.reason), reported_by: c.sub, reported_at: nowIso() });
  }
  recordAudit(c, "idp.document_rollback", "source_documents", d.id, String(b.reason));
  return ok({ document: docOut(c, d), reverted_actions: actionRefs(reverted) });
}

function form(req: MockRequest): Response {
  const code = req.params.type ?? "";
  const t = captureStore().docTypes.find((x) => x.code === code && x.is_active);
  const s = captureStore().schemas.find((x) => x.document_type === code && x.status === "published");
  if (!t || !s) throw err(404, "NOT_FOUND", "no form for this document type");
  const fields = s.fields.filter((f) => f.sensitivity_level < 4 || seesLevel4(req.claims)).map((f) => ({ name: f.name, label_key: f.label_key, value_type: f.value_type, required: f.required,
    is_critical: f.is_critical, sensitivity_level: f.sensitivity_level, enum: f.enum, master_ref: f.master_ref, repeatable_group: f.group === "row" ? "rows" : null }));
  const acts = s.action_names;
  return ok({ document_type: code, schema_version: s.schema_version, fields, required_permissions: [...new Set(acts.flatMap((a) => (a === "ACT-create_employee" ? ["hr:write"] : a === "ACT-create_department" ? ["hr:admin"] : a === "ACT-create_invoice" ? ["finance:write"] : ["execution:write"])))],
    permitted: acts.every((a) => actPermitted(req.claims, a, true)) });
}

/** EP-DC-16 C1: validate (fail → 422 per field, nothing created) → COMMITTED when permitted, else NEEDS_REVIEW. */
function manual(req: MockRequest): Response {
  requireIdem(req);
  const c = req.claims;
  const b = body(req);
  const code = String(b.document_type ?? "");
  const s = captureStore().schemas.find((x) => x.document_type === code && x.status === "published");
  if (!s) throw err(422, "VALIDATION_ERROR", "unknown document_type", { field: "document_type" });
  if (b.schema_version !== s.schema_version) throw err(409, "CONFLICT_STATE", "schema version changed", { schema_version: s.schema_version });
  const header = s.fields.filter((f) => f.group !== "row");
  const rowDefs = s.fields.filter((f) => f.group === "row");
  const values = (b.values && typeof b.values === "object" ? b.values : {}) as Record<string, unknown>;
  const rows = (Array.isArray(b.rows) ? b.rows : []) as Record<string, unknown>[];
  const hv = validateValues(header, values);
  const rv = rows.map((r) => validateValues(rowDefs, r));
  const errors: (RowError & { row_index: number | null })[] = [...hv.errors.map((e) => ({ ...e, row_index: null })), ...rv.flatMap((r, i) => r.errors.map((e) => ({ ...e, row_index: i })))];
  if (errors.length) throw err(422, "VALIDATION_ERROR", "invalid values", { fields: errors });
  const id = newCaptureId("document");
  const u = c.name;
  const d = docBase({ id, submitter: c.email, channel: "C1", kind: "MANUAL", status: "VALIDATING", document_type: code, schema_version: s.schema_version, document_confidence: 1, submitted_at: nowIso(),
    pillars: code === "HR_ROSTER" ? ["O"] : code === "INVOICE" ? ["F"] : [], submitted_by_name: u });
  d.fields = [...makeFields(id, s.fields, hv.values, null, 1), ...rv.flatMap((r, i) => makeFields(id, s.fields, r.values, i, 1))].map((f) => ({ ...f, confidence: 1, is_confirmed: true }));
  const permitted = plannedActions(c, d).every((p) => p.permitted);
  captureStore().docs.push(d);
  recordAudit(c, "idp.manual_submit", "source_documents", d.id);
  if (permitted) {
    const out = finishCommit(req, d);
    return ok({ document: out.document, status: d.status, actions: out.actions, validation_errors: [], undo_deadline: out.undo_deadline }, 201);
  }
  Object.assign(d, { status: "NEEDS_REVIEW", routing_reasons: ["MISSING_TARGET_PERMISSION"], assigned_to: reviewerFor() });
  return ok({ document: docOut(c, d), status: d.status, actions: [], validation_errors: [], undo_deadline: null }, 201);
}

/** Review routing: REV handles the queue (DIR/MGR see it by scope). */
const reviewerFor = (): string => userId(REVIEWER);

const R = "idp:read";
const W = "idp:write";
export const CAPTURE_ROUTES: readonly Route[] = [
  { method: "GET", pattern: "/data-capture/inbox", permission: R, handler: inbox },
  { method: "GET", pattern: "/data-capture/forms/:type", permission: W, handler: form },
  { method: "POST", pattern: "/data-capture/manual", permission: W, handler: manual },
  { method: "GET", pattern: "/data-capture/documents/:id/source", permission: R, handler: source },
  { method: "POST", pattern: "/data-capture/documents/:id/commit", permission: W, handler: commit },
  { method: "POST", pattern: "/data-capture/documents/:id/undo", permission: W, handler: undo },
  { method: "GET", pattern: "/data-capture/documents/:id/actions", permission: R, handler: actions },
  { method: "GET", pattern: "/lineage/:entity/:id", permission: R, handler: lineage },
  ...CAPTURE_IMPORT_ROUTES,
  ...CAPTURE_REVIEW_ROUTES,
  ...CAPTURE_ADMIN_ROUTES,
];

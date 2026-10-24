/**
 * Mock C5 import EP-DC-17..22: upload → preview (sheets, suggested type, column mapping, ≤ 20 preview
 * rows, summary) → mapping PATCH (422 `unmapped_required[]`, 409 when not VALIDATING / stale
 * version, submitter only) → rows by status → error file (.xlsx, 404 when none) → submit valid rows
 * as one NEEDS_REVIEW document (field `row_index` = sheet row; 422 `no_valid_rows`).
 */
import { ok } from "./http";
import { recordAudit } from "./audit";
import type { MockRequest, Route } from "./router";
import { seesLevel4 } from "./capture-scope";
import { captureStore, newCaptureId, nowIso, REVIEWER, userId, type MBatch } from "./capture-store";
import { docBase, makeFields } from "./capture-seed";
import { SCHEMA_FIELDS } from "./capture-schemas";
import { body, docOut, err, expectVersion, requireIdem } from "./capture-out";
import { autoMap, evaluate, headersOf, loadSheets, rowFields, suggest, unmappedRequired, type UploadMeta } from "./capture-import-parse";
import { xlsxBytes } from "./capture-xlsx";

function previewOut(req: MockRequest, b: MBatch) {
  const rows = evaluate(b);
  const invalid = rows.filter((r) => r.errors.length).length;
  return { batch_id: b.id, document_id: b.document_id, version: b.version, suggested_document_type: b.suggested, column_mapping: b.mapping,
    sheets: b.sheets.map((s) => ({ name: s.name, row_count: Math.max(0, s.rows.length - 1), header_row: b.header_row, columns: (s.name === b.sheet ? headersOf(b) : s.rows[0] ?? []).map((h, index) => ({ index, header: h || null })) })),
    preview_rows: rows.slice(0, 20).map((r) => maskRow(req, r.values)), summary: { rows_total: rows.length, rows_valid: rows.length - invalid, rows_invalid: invalid } };
}

function maskRow(req: MockRequest, v: Record<string, unknown>) {
  if (seesLevel4(req.claims)) return v;
  const lvl4 = new Set(Object.values(SCHEMA_FIELDS).flat().filter((f) => f.sensitivity_level >= 4).map((f) => f.name));
  return Object.fromEntries(Object.entries(v).map(([k, x]) => [k, lvl4.has(k) && x !== null ? { masked: true } : x]));
}

function upload(req: MockRequest): Response {
  requireIdem(req);
  const p = body(req);
  const f = p.file as UploadMeta | null;
  if (!f?.name) throw err(422, "VALIDATION_ERROR", "file is required", { field: "file" });
  if (f.size > 50 * 1024 * 1024) throw err(413, "FILE_TOO_LARGE", "file exceeds 50 MB", { limit: "size" });
  const s = captureStore();
  const prior = s.docs.find((d) => d.channel === "C5" && d.original_filename === f.name && d.size_bytes === f.size && !["REJECTED", "ROLLED_BACK", "FAILED"].includes(d.status));
  if (prior) throw err(409, "DUPLICATE_RESOURCE", "the same file was already imported", { duplicate_of_id: prior.id });
  const sheets = loadSheets(f);
  const type = p.document_type ? String(p.document_type) : null;
  if (type && !s.docTypes.some((t) => t.code === type && t.is_active)) throw err(422, "VALIDATION_ERROR", "unknown document_type", { field: "document_type" });
  const b: MBatch = { id: newCaptureId("batch"), document_id: newCaptureId("document"), version: 1, submitted_by: req.claims.sub, status: "VALIDATING", filename: f.name,
    sheets, sheet: sheets[0]!.name, header_row: 1, document_type: type, suggested: null, mapping: {} };
  b.suggested = suggest(headersOf(b));
  b.document_type ??= b.suggested?.code ?? null;
  b.mapping = autoMap(b.document_type, headersOf(b));
  s.docs.push(docBase({ id: b.document_id, submitter: req.claims.email, submitted_by_name: req.claims.name, original_filename: f.name, size_bytes: f.size, channel: "C5", status: "VALIDATING",
    mime_type: f.type || null, document_type: b.document_type, batch_id: b.id, sheet_name: b.sheet, submitted_at: nowIso(), page_count: sheets.length }));
  s.batches.push(b);
  recordAudit(req.claims, "idp.import_upload", "import_batches", b.id);
  return ok(previewOut(req, b), 201);
}

function batchOf(req: MockRequest, owner = false): MBatch {
  const b = captureStore().batches.find((x) => x.id === req.params.id);
  const d = b && captureStore().docs.find((x) => x.id === b.document_id);
  if (!b || !d) throw err(404, "NOT_FOUND", "import batch not found");
  if (b.submitted_by !== req.claims.sub && (owner || req.claims.role !== "CEO")) throw err(404, "NOT_FOUND", "import batch not found");
  return b;
}

function mapping(req: MockRequest): Response {
  const b = batchOf(req, true);
  if (b.status !== "VALIDATING") throw err(409, "CONFLICT_STATE", "batch already submitted", { status: b.status });
  expectVersion(req, b.version);
  const p = body(req);
  const type = String(p.document_type ?? "");
  if (!SCHEMA_FIELDS[type]) throw err(422, "VALIDATION_ERROR", "unknown document_type", { field: "document_type" });
  const sheet = String(p.sheet ?? "");
  if (!b.sheets.some((s) => s.name === sheet)) throw err(422, "VALIDATION_ERROR", "unknown sheet", { field: "sheet" });
  const hr = Number(p.header_row);
  if (!Number.isInteger(hr) || hr < 1 || hr > 50) throw err(422, "VALIDATION_ERROR", "header_row must be 1..50", { field: "header_row" });
  const m = (p.mapping && typeof p.mapping === "object" ? p.mapping : {}) as Record<string, string | null>;
  const names = new Set(rowFields(type).map((f) => f.name));
  const next = Object.fromEntries(Object.entries(m).map(([h, fld]) => {
    if (fld !== null && !names.has(fld)) throw err(422, "VALIDATION_ERROR", "unknown field", { field: "mapping", header: h });
    return [h, { field: fld, confidence: fld && b.mapping[h]?.field === fld ? b.mapping[h]!.confidence : fld ? 1 : 0 }];
  }));
  const missing = unmappedRequired(type, next);
  if (missing.length) throw err(422, "VALIDATION_ERROR", "required fields are not mapped", { unmapped_required: missing });
  Object.assign(b, { document_type: type, sheet, header_row: hr, mapping: next, version: b.version + 1 });
  return ok(previewOut(req, b));
}

function rows(req: MockRequest): Response {
  const b = batchOf(req);
  const st = req.query.get("status") ?? "all";
  if (!["valid", "invalid", "all"].includes(st)) throw err(422, "VALIDATION_ERROR", "status must be valid|invalid|all", { field: "status" });
  const all = evaluate(b).filter((r) => st === "all" || (st === "valid" ? r.errors.length === 0 : r.errors.length > 0));
  const limit = Math.min(Number(req.query.get("limit") ?? 20) || 20, 100);
  const offset = Number(req.query.get("offset") ?? 0) || 0;
  const data = all.slice(offset, offset + limit).map((r) => ({ ...r, values: maskRow(req, r.values) }));
  return ok(data, 200, { pagination: { total: all.length, limit, offset, has_next: offset + data.length < all.length } });
}

function errorFile(req: MockRequest): Response {
  const b = batchOf(req);
  const bad = evaluate(b).filter((r) => r.errors.length);
  if (!bad.length) throw err(404, "NOT_FOUND", "no error rows");
  const sheet = b.sheets.find((s) => s.name === b.sheet)!;
  const out = [[...(sheet.rows[b.header_row - 1] ?? []), "Lỗi"], ...bad.map((r) => [...(sheet.rows[r.row_number - 1] ?? []), r.errors.map((e) => `${e.field ?? ""}: ${e.rule_code}`).join("; ")])];
  return new Response(xlsxBytes(b.sheet, out) as BodyInit, { status: 200, headers: { "content-type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "content-disposition": `attachment; filename="loi-${b.filename.replace(/\.(xlsx|csv)$/i, "")}.xlsx"` } });
}

function submit(req: MockRequest): Response {
  requireIdem(req);
  const b = batchOf(req, true);
  if (b.status !== "VALIDATING") throw err(409, "CONFLICT_STATE", "batch already submitted", { status: b.status });
  expectVersion(req, b.version);
  const all = evaluate(b);
  const valid = all.filter((r) => r.errors.length === 0);
  if (!valid.length) throw err(422, "BUSINESS_RULE_VIOLATION", "no valid rows", { reason: "no_valid_rows" });
  const d = captureStore().docs.find((x) => x.id === b.document_id)!;
  const defs = (SCHEMA_FIELDS[b.document_type ?? ""] ?? []).filter((f) => f.group === "row" && (seesLevel4(req.claims) || f.sensitivity_level < 4));
  d.fields = valid.flatMap((r) => makeFields(d.id, defs, r.values, r.row_number, 0.97, { kind: "sheet", sheet: b.sheet }));
  Object.assign(d, { status: "NEEDS_REVIEW", document_type: b.document_type, sheet_name: b.sheet, routing_reasons: ["C5_REVIEW"], assigned_to: userId(REVIEWER), document_confidence: 0.97,
    pillars: b.document_type === "HR_ROSTER" ? ["O"] : [], sensitivity_level: defs.some((f) => f.sensitivity_level >= 4) ? 4 : 2, version: d.version + 1 });
  Object.assign(b, { status: "SUBMITTED", version: b.version + 1 });
  recordAudit(req.claims, "idp.import_submit", "import_batches", b.id);
  return ok({ document: docOut(req.claims, d), rows_submitted: valid.length, rows_excluded: all.length - valid.length });
}

export const CAPTURE_IMPORT_ROUTES: readonly Route[] = [
  { method: "POST", pattern: "/data-capture/imports", permission: "idp:write", handler: upload },
  { method: "GET", pattern: "/data-capture/imports/:id", permission: "idp:read", handler: (req) => ok(previewOut(req, batchOf(req))) },
  { method: "PATCH", pattern: "/data-capture/imports/:id/mapping", permission: "idp:write", handler: mapping },
  { method: "GET", pattern: "/data-capture/imports/:id/rows", permission: "idp:read", handler: rows },
  { method: "GET", pattern: "/data-capture/imports/:id/error-file", permission: "idp:read", handler: errorFile },
  { method: "POST", pattern: "/data-capture/imports/:id/submit", permission: "idp:write", handler: submit },
];

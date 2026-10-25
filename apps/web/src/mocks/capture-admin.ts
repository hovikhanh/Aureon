/**
 * Mock SCR-63 config EP-DC-27..35 + incidents EP-DC-36/37 (R-DEC-65/69, 10 §7.2.4): doc types
 * (read `idp:read`, patch `idp:admin`), ExtractionSchema draft → publish (old → retired), rule
 * guards (thresholds ≥ 0.95 / 0.90, critical names stay critical, known ACT, known `op`,
 * duplicate code 409, only draft schemas editable), incidents (`idp:approve`).
 */
import { ok } from "./http";
import { recordAudit } from "./audit";
import type { MockRequest, Route } from "./router";
import { ACT_PERMISSION, CRITICAL_FIELD_NAMES, VALIDATOR_OPS, type FieldDef } from "./capture-schemas";
import { captureStore, newCaptureId, nowIso, type MSchema } from "./capture-store";
import { body, err, expectVersion, requireIdem } from "./capture-out";
import { docVisible } from "./capture-scope";

const typeOut = (t: ReturnType<typeof captureStore>["docTypes"][number]) => {
  const pub = captureStore().schemas.find((s) => s.document_type === t.code && s.status === "published");
  return { id: t.id, version: t.version, code: t.code, name_vi: t.name_vi, name_en: t.name_en, pillars: t.pillars, is_active: t.is_active, current_schema_version: pub?.schema_version ?? null, channels_supported: t.channels_supported };
};
const schemaOut = (s: MSchema) => ({ ...s });

function patchType(req: MockRequest): Response {
  const t = captureStore().docTypes.find((x) => x.id === req.params.id);
  if (!t) throw err(404, "NOT_FOUND", "document type not found");
  expectVersion(req, t.version);
  const b = body(req);
  for (const k of ["name_vi", "name_en"] as const) if (typeof b[k] === "string") t[k] = String(b[k]);
  if (typeof b.is_active === "boolean") t.is_active = b.is_active;
  if (Array.isArray(b.classifier_keywords)) t.classifier_keywords = b.classifier_keywords.map(String);
  t.version += 1;
  recordAudit(req.claims, "idp.document_type_update", "document_types", t.id);
  return ok(typeOut(t));
}

function checkSchema(fields: FieldDef[], th: MSchema["thresholds"], acts: string[]): void {
  if (th.classification_confidence_min < 0.95 || th.required_field_min < 0.9) throw err(422, "VALIDATION_ERROR", "thresholds below the minimum", { field: "thresholds", min: { classification_confidence_min: 0.95, required_field_min: 0.9 } });
  const lost = fields.filter((f) => !f.is_critical && (CRITICAL_FIELD_NAMES.includes(f.name) || ["money", "tax_code"].includes(f.value_type) || f.sensitivity_level >= 4)).map((f) => f.name);
  if (lost.length) throw err(422, "VALIDATION_ERROR", "critical fields must stay critical", { field: "fields", fields: lost });
  const bad = acts.filter((a) => !ACT_PERMISSION[a]);
  if (bad.length) throw err(422, "VALIDATION_ERROR", "unknown action", { field: "action_names", unknown: bad });
  const target = fields.filter((f) => f.target && !acts.includes(f.target.action)).map((f) => f.name);
  if (target.length) throw err(422, "VALIDATION_ERROR", "field target action not in action_names", { field: "fields", fields: target });
}

function createSchema(req: MockRequest): Response {
  requireIdem(req);
  const s = captureStore();
  const b = body(req);
  const code = String(b.document_type ?? "");
  if (!s.docTypes.some((t) => t.code === code)) throw err(422, "VALIDATION_ERROR", "unknown document_type", { field: "document_type" });
  if (s.schemas.some((x) => x.document_type === code && x.status === "draft")) throw err(409, "CONFLICT_STATE", "a draft already exists", { document_type: code });
  const from = b.clone_from_id ? s.schemas.find((x) => x.id === b.clone_from_id) : undefined;
  if (b.clone_from_id && !from) throw err(422, "VALIDATION_ERROR", "clone source not found", { field: "clone_from_id" });
  const fields = (Array.isArray(b.fields) && b.fields.length ? b.fields : from?.fields ?? []) as FieldDef[];
  const th = (b.thresholds as MSchema["thresholds"] | undefined) ?? from?.thresholds ?? { classification_confidence_min: 0.95, required_field_min: 0.9 };
  const acts = (Array.isArray(b.action_names) && b.action_names.length ? b.action_names : from?.action_names ?? []) as string[];
  checkSchema(fields, th, acts);
  const max = Math.max(0, ...s.schemas.filter((x) => x.document_type === code).map((x) => x.schema_version));
  const row: MSchema = { id: newCaptureId("extraction_schema"), version: 1, document_type: code, schema_version: max + 1, status: "draft", fields: structuredClone(fields), thresholds: { ...th }, action_names: [...acts], published_at: null };
  s.schemas.push(row);
  recordAudit(req.claims, "idp.schema_create", "extraction_schemas", row.id);
  return ok(schemaOut(row), 201);
}

function draftOf(id: string | undefined): MSchema {
  const row = captureStore().schemas.find((x) => x.id === id);
  if (!row) throw err(404, "NOT_FOUND", "extraction schema not found");
  if (row.status !== "draft") throw err(409, "CONFLICT_STATE", "only draft schemas can change", { status: row.status });
  return row;
}

function patchSchema(req: MockRequest): Response {
  const row = draftOf(req.params.id);
  expectVersion(req, row.version);
  const b = body(req);
  const fields = (Array.isArray(b.fields) ? b.fields : row.fields) as FieldDef[];
  const th = (b.thresholds as MSchema["thresholds"] | undefined) ?? row.thresholds;
  const acts = (Array.isArray(b.action_names) ? b.action_names : row.action_names) as string[];
  checkSchema(fields, th, acts);
  Object.assign(row, { fields, thresholds: th, action_names: acts, version: row.version + 1 });
  return ok(schemaOut(row));
}

function publish(req: MockRequest): Response {
  requireIdem(req);
  const row = draftOf(req.params.id);
  expectVersion(req, row.version);
  for (const x of captureStore().schemas) if (x.document_type === row.document_type && x.status === "published") Object.assign(x, { status: "retired", version: x.version + 1 });
  Object.assign(row, { status: "published", published_at: nowIso(), version: row.version + 1 });
  recordAudit(req.claims, "idp.schema_publish", "extraction_schemas", row.id);
  return ok(schemaOut(row));
}

const KINDS = ["field", "cross_field", "cross_document", "master_data"];
const SEVERITIES = ["warn", "fail", "blocking"];
function checkExpr(e: unknown): Record<string, unknown> {
  const x = (e && typeof e === "object" ? e : {}) as Record<string, unknown>;
  if (!VALIDATOR_OPS.includes(String(x.op))) throw err(422, "VALIDATION_ERROR", "unknown op", { field: "expression", allowed: VALIDATOR_OPS.join(",") });
  return x;
}

function createRule(req: MockRequest): Response {
  requireIdem(req);
  const s = captureStore();
  const b = body(req);
  const sid = b.extraction_schema_id ? String(b.extraction_schema_id) : null;
  if (sid) draftOf(sid);
  const code = String(b.code ?? "").trim();
  if (!code) throw err(422, "VALIDATION_ERROR", "code is required", { field: "code" });
  if (!KINDS.includes(String(b.kind))) throw err(422, "VALIDATION_ERROR", "invalid kind", { field: "kind" });
  if (!SEVERITIES.includes(String(b.severity))) throw err(422, "VALIDATION_ERROR", "invalid severity", { field: "severity" });
  const expression = checkExpr(b.expression);
  if (s.rules.some((r) => r.code === code && r.extraction_schema_id === sid)) throw err(409, "DUPLICATE_RESOURCE", "rule code exists", { field: "code" });
  const row = { id: newCaptureId("validation_rule"), version: 1, extraction_schema_id: sid, code, kind: String(b.kind), expression, severity: String(b.severity), tolerance: typeof b.tolerance === "number" ? b.tolerance : null, is_active: true };
  s.rules.push(row);
  return ok(row, 201);
}

function patchRule(req: MockRequest): Response {
  const row = captureStore().rules.find((x) => x.id === req.params.id);
  if (!row) throw err(404, "NOT_FOUND", "validation rule not found");
  if (row.extraction_schema_id) draftOf(row.extraction_schema_id);
  expectVersion(req, row.version);
  const b = body(req);
  if (b.expression !== undefined && b.expression !== null) row.expression = checkExpr(b.expression);
  if (b.severity) { if (!SEVERITIES.includes(String(b.severity))) throw err(422, "VALIDATION_ERROR", "invalid severity", { field: "severity" }); row.severity = String(b.severity); }
  if (typeof b.tolerance === "number") row.tolerance = b.tolerance;
  if (typeof b.is_active === "boolean") row.is_active = b.is_active;
  row.version += 1;
  return ok(row);
}

function createIncident(req: MockRequest): Response {
  requireIdem(req);
  const b = body(req);
  const d = captureStore().docs.find((x) => x.id === b.source_document_id);
  if (!d || !docVisible(req.claims, d)) throw err(404, "NOT_FOUND", "document not found");
  if (!String(b.field_name ?? "").trim() || !String(b.description ?? "").trim()) throw err(422, "VALIDATION_ERROR", "field_name and description are required", { field: !String(b.field_name ?? "").trim() ? "field_name" : "description" });
  const f = d.fields.find((x) => x.id === b.extracted_field_id || x.field_name === b.field_name);
  const row = { id: newCaptureId("incident"), source_document_id: d.id, extracted_field_id: f?.id ?? null, field_name: String(b.field_name), is_critical: f?.is_critical ?? false,
    detected_by: (d.status === "COMMITTED" ? "post_commit" : "review") as "post_commit" | "review", undetected: d.status === "COMMITTED", target_table: (b.target_table as string) ?? null,
    target_id: (b.target_id as string) ?? null, description: String(b.description), reported_by: req.claims.sub, reported_at: nowIso() };
  captureStore().incidents.push(row);
  recordAudit(req.claims, "idp.incident_create", "incidents", row.id);
  return ok(row, 201);
}

function listIncidents(req: MockRequest): Response {
  const period = req.query.get("period");
  const und = req.query.get("undetected_only") === "true";
  const docs = new Map(captureStore().docs.map((d) => [d.id, d]));
  const inScope = (i: { source_document_id: string; reported_by: string }) => {
    const d = docs.get(i.source_document_id);
    return i.reported_by === req.claims.sub || (d !== undefined && docVisible(req.claims, d)); // BE: inbox scope ∪ own reports
  };
  const rows = captureStore().incidents.filter((i) => inScope(i) && (!period || i.reported_at.startsWith(period)) && (!und || i.undetected)).sort((a, b) => b.reported_at.localeCompare(a.reported_at));
  const limit = Math.min(Number(req.query.get("limit") ?? 20) || 20, 100);
  const offset = Number(req.query.get("offset") ?? 0) || 0;
  return ok(rows.slice(offset, offset + limit), 200, { pagination: { total: rows.length, limit, offset, has_next: offset + limit < rows.length } });
}

const q = (req: MockRequest, k: string) => req.query.get(k);
export const CAPTURE_ADMIN_ROUTES: readonly Route[] = [
  { method: "GET", pattern: "/data-capture/document-types", permission: "idp:read", handler: (req) => ok(captureStore().docTypes.filter((t) => t.is_active || q(req, "include_inactive") === "true").map(typeOut)) },
  { method: "PATCH", pattern: "/data-capture/document-types/:id", permission: "idp:admin", handler: patchType },
  { method: "GET", pattern: "/data-capture/extraction-schemas", permission: "idp:admin", handler: (req) => ok(captureStore().schemas.filter((s) => (!q(req, "document_type") || s.document_type === q(req, "document_type")) && (!q(req, "status") || s.status === q(req, "status"))).map(schemaOut)) },
  { method: "POST", pattern: "/data-capture/extraction-schemas", permission: "idp:admin", handler: createSchema },
  { method: "PATCH", pattern: "/data-capture/extraction-schemas/:id", permission: "idp:admin", handler: patchSchema },
  { method: "POST", pattern: "/data-capture/extraction-schemas/:id/publish", permission: "idp:admin", handler: publish },
  { method: "GET", pattern: "/data-capture/validation-rules", permission: "idp:admin", handler: (req) => ok(captureStore().rules.filter((r) => (!q(req, "extraction_schema_id") || r.extraction_schema_id === q(req, "extraction_schema_id")) && (!q(req, "kind") || r.kind === q(req, "kind")))) },
  { method: "POST", pattern: "/data-capture/validation-rules", permission: "idp:admin", handler: createRule },
  { method: "PATCH", pattern: "/data-capture/validation-rules/:id", permission: "idp:admin", handler: patchRule },
  { method: "POST", pattern: "/data-capture/incidents", permission: "idp:approve", handler: createIncident },
  { method: "GET", pattern: "/data-capture/incidents", permission: "idp:approve", handler: listIncidents },
];

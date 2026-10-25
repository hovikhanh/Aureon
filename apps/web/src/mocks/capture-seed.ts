/**
 * Mock D03 seed (mock-only until the M1.5 BE seed exists): 5 doc types + schema v1 published +
 * rules, and ~8 documents spread over every inbox group so SCR-45 tabs/counts are populated:
 * an HR_ROSTER C5 doc waiting for review (REV assigned), a C3 invoice processing, a C1 KPI
 * committed by the CEO (undoable), one rejected, one failed, one rolled back, and the EMP's own
 * C1 task committed. Ids are deterministic (`mockId`).
 */
import { SNAPSHOT, mockId } from "./fixtures";
import { DOC_TYPES, SCHEMA_FIELDS, type FieldDef } from "./capture-schemas";
import type { CaptureStore, MDoc, MField, MSchema } from "./capture-store";
import data from "./capture-data.json";

const STAMP = "2026-10-20T02:00:00Z";
const uid = (email: string) => mockId("user", email);
const user = (email: string) => SNAPSHOT.users.find((u) => u.email === email)!;
const did = (code: string) => mockId("department", code);

export const SEED_DOC = {
  roster: mockId("document", "CAP-ROSTER"), invoice: mockId("document", "CAP-INV"), kpi: mockId("document", "CAP-KPI"),
  rejected: mockId("document", "CAP-REJ"), failed: mockId("document", "CAP-FAIL"), rolled: mockId("document", "CAP-ROLL"), empTask: mockId("document", "CAP-EMP"),
};

export function docBase(p: Partial<MDoc> & { id: string; submitter: string }): MDoc {
  const u = user(p.submitter);
  return {
    version: 1, original_filename: null, mime_type: null, size_bytes: null, page_count: null, channel: "C3", kind: "FILE", status: "UPLOADED", status_reason: null,
    pillars: [], sensitivity_level: 2, submitted_at: STAMP, document_type: null, committed_at: null, undo_deadline: null, rolled_back_at: null,
    submitted_by: uid(u.email), submitted_by_name: u.full_name, department_id: did(u.department), assigned_to: null, approved_by: null,
    locked_by: null, locked_until: null, batch_id: null, sheet_name: null, schema_version: 1, fields: [], actions: [], document_confidence: null, routing_reasons: [], ...p,
  };
}

/** Header fields (row_index=null) or one row of fields, confidence per value. */
export function makeFields(docId: string, defs: readonly FieldDef[], values: Record<string, unknown>, rowIndex: number | null, confidence = 0.97, loc: Record<string, unknown> = {}): MField[] {
  return defs.filter((d) => (rowIndex === null ? d.group !== "row" : d.group === "row")).map((d) => ({
    id: mockId("field", `${docId}:${rowIndex ?? "h"}:${d.name}`), field_name: d.name, row_index: rowIndex, value_type: d.value_type, ai_value: values[d.name] ?? null,
    corrected_value: null, confidence: d.is_critical ? Math.min(confidence, 0.93) : confidence, is_critical: d.is_critical, is_confirmed: false, sensitivity_level: d.sensitivity_level,
    source_location: { ...loc, ...(rowIndex !== null ? { row: rowIndex } : {}) }, validation: [], correction_reason: null,
  }));
}

function rosterDoc(): MDoc {
  const id = SEED_DOC.roster;
  const defs = SCHEMA_FIELDS.HR_ROSTER!;
  const sheet = data.hr.sheets[0]!;
  const head = sheet.rows[0]!.map((h) => h.toLowerCase());
  const col = (d: FieldDef) => head.findIndex((h) => d.header_aliases.includes(h));
  const fields = sheet.rows.slice(1, 4).flatMap((r, i) => makeFields(id, defs, Object.fromEntries(defs.map((d) => [d.name, r[col(d)] || null])), i + 2, 0.95, { kind: "sheet", sheet: sheet.name }));
  return docBase({ id, submitter: "hr@abc.demo", original_filename: "DS-nhan-su-moi-T10.xlsx", mime_type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    channel: "C5", status: "NEEDS_REVIEW", document_type: "HR_ROSTER", pillars: ["O"], sensitivity_level: 4, assigned_to: uid("reviewer@abc.demo"), sheet_name: sheet.name,
    fields, document_confidence: 0.95, routing_reasons: ["C5_REVIEW"], submitted_at: "2026-10-19T03:00:00Z" });
}

function schemaOf(code: string): MSchema {
  return { id: mockId("extraction_schema", `${code}:1`), version: 1, document_type: code, schema_version: 1, status: "published", fields: SCHEMA_FIELDS[code] ?? [],
    thresholds: { classification_confidence_min: 0.95, required_field_min: 0.9 }, published_at: STAMP,
    action_names: [...new Set((SCHEMA_FIELDS[code] ?? []).flatMap((f) => (f.target ? [f.target.action] : [])))] };
}

export function seedCapture(): CaptureStore {
  const docTypes = DOC_TYPES.map((t) => ({ id: mockId("document_type", t.code), version: 1, code: t.code, name_vi: t.name_vi, name_en: t.name_en, pillars: t.pillars, is_active: true, channels_supported: t.channels, classifier_keywords: t.keywords }));
  const schemas = DOC_TYPES.map((t) => schemaOf(t.code));
  const hr = schemas.find((s) => s.document_type === "HR_ROSTER")!;
  const rules = [
    { id: mockId("validation_rule", "HR-HIRE"), version: 1, extraction_schema_id: hr.id, code: "HR_HIRE_NOT_FUTURE", kind: "field", expression: { field: "hire_date", op: "date_not_future" }, severity: "fail", tolerance: null, is_active: true },
    { id: mockId("validation_rule", "HR-STATUS"), version: 1, extraction_schema_id: hr.id, code: "HR_STATUS_IN", kind: "field", expression: { field: "status", op: "in", values: ["ACTIVE", "PROBATION", "ON_LEAVE", "TERMINATED"] }, severity: "fail", tolerance: null, is_active: true },
  ];
  const committed = "2026-10-21T04:00:00Z";
  const days7 = (iso: string) => new Date(Date.parse(iso) + 7 * 86_400_000).toISOString();
  const docs: MDoc[] = [
    rosterDoc(),
    docBase({ id: SEED_DOC.invoice, submitter: "cfo@abc.demo", original_filename: "HD-0001234.pdf", mime_type: "application/pdf", page_count: 1, status: "EXTRACTING", document_type: "INVOICE", pillars: ["F"], submitted_at: "2026-10-20T08:00:00Z" }),
    docBase({ id: SEED_DOC.kpi, submitter: "ceo@abc.demo", channel: "C1", kind: "MANUAL", status: "COMMITTED", document_type: "PLAN_KPI_OKR", committed_at: committed, undo_deadline: days7(committed), approved_by: uid("ceo@abc.demo"), submitted_at: committed, document_confidence: 1 }),
    docBase({ id: SEED_DOC.rejected, submitter: "manager@abc.demo", original_filename: "bao-cao-T9.pdf", mime_type: "application/pdf", page_count: 2, status: "REJECTED", status_reason: "Sai kỳ báo cáo", document_type: "PERIOD_REPORT", submitted_at: "2026-10-15T02:00:00Z" }),
    docBase({ id: SEED_DOC.failed, submitter: "manager@abc.demo", original_filename: "scan-mo.jpg", mime_type: "image/jpeg", page_count: 1, status: "FAILED", status_reason: "ocr_failed", submitted_at: "2026-10-16T02:00:00Z" }),
    docBase({ id: SEED_DOC.rolled, submitter: "sales@abc.demo", channel: "C1", kind: "MANUAL", status: "ROLLED_BACK", document_type: "PLAN_KPI_OKR", pillars: [], committed_at: "2026-10-12T02:00:00Z", rolled_back_at: "2026-10-12T05:00:00Z", submitted_at: "2026-10-12T02:00:00Z" }),
    docBase({ id: SEED_DOC.empTask, submitter: "employee@abc.demo", channel: "C1", kind: "MANUAL", status: "COMMITTED", document_type: "PLAN_KPI_OKR", committed_at: committed, undo_deadline: days7(committed), approved_by: uid("employee@abc.demo"), submitted_at: committed, document_confidence: 1 }),
  ];
  return { docs, batches: [], lineage: [], docTypes, schemas, rules, incidents: [], idem: new Map(), seq: 0 };
}

/**
 * Mock ACT targets — write into the org / work / goals mock stores (the way the real ACT calls the
 * target module's public service with the request session). Each ref keeps the target `version`
 * at commit time so undo can detect "edited after commit" (R-DEC-63).
 */
import { SNAPSHOT, mockId, type MockClaims } from "./fixtures";
import { orgStore, today, type MDept, type MEmployee, type MPosition } from "./org";
import { task, workStore, employeeOf } from "./work-store";
import { goalStore, base as goalBase, type MKpi } from "./goals-store";
import { ACT_TABLE, SCHEMA_FIELDS } from "./capture-schemas";
import { captureStore, newCaptureId, type MDoc, type MResultRef } from "./capture-store";
import type { Row } from "./capture-actions";

const SNAP_EMPLOYEE_CODES = new Set(SNAPSHOT.employees.map((e) => e.code));
const sourceOf = (d: MDoc) => (d.channel === "C5" ? "IMPORT" : d.channel === "C1" ? "MANUAL" : "IDP");
const str = (v: unknown) => (v === null || v === undefined ? "" : String(v).trim());

function liveDept(code: string): MDept | undefined {
  return orgStore().depts.find((x) => !x.archived && x.code === code);
}
function employeeCodeTaken(code: string): boolean {
  const s = orgStore();
  return SNAP_EMPLOYEE_CODES.has(code) || s.employees.some((e) => !e.deleted && e.code === code);
}

/** Target duplicate that the ACT reports as a row error (10 §7.2.4 "Khóa upsert / trùng"). */
export function actDuplicate(action: string, v: Record<string, unknown>): string | null {
  if (action === "ACT-create_employee" && employeeCodeTaken(str(v.employee_code))) return "employee_code";
  return null;
}

function lineage(d: MDoc, action: string, r: Row, entity: string, id: string, at: string): void {
  const defs = SCHEMA_FIELDS[d.document_type ?? ""] ?? [];
  for (const f of r.fields) {
    const def = defs.find((x) => x.name === f.field_name);
    if (!def?.target || def.target.action !== action || str(r.values[f.field_name]) === "") continue;
    captureStore().lineage.push({ entity, record_id: id, document_id: d.id, action_name: action, row_index: r.row_index, field_name: f.field_name, target_column: def.target.param,
      raw_text: str(f.ai_value), confidence: f.confidence, committed_at: at, revoked_at: null, sensitivity_level: def.sensitivity_level });
  }
}

const ref = (schema: string, table: string, id: string, version: number, reused = false): MResultRef => ({ schema, table, id, reused, snapshot: { version } });

export function runAct(c: MockClaims, d: MDoc, action: string, r: Row, created: Map<string, string>, at: string): MResultRef {
  const v = r.values;
  if (action === "ACT-create_department") {
    const code = str(v.department_code);
    const hit = liveDept(code);
    if (hit) return ref("hr", "departments", hit.id, hit.version, true);
    const row: MDept = { id: newCaptureId("department"), version: 1, organization_id: orgStore().depts[0]?.organization_id ?? "", code, name: str(v.department_name) || code, parent_id: null, manager_id: null,
      valid_from: today(), valid_to: null, archived: false, created_at: at, updated_at: at };
    orgStore().depts.push(row);
    created.set(`dept:${code}`, row.id);
    lineage(d, action, r, "hr.departments", row.id, at);
    return ref("hr", "departments", row.id, 1);
  }
  if (action === "ACT-create_position") {
    const dept = liveDept(str(v.department_code));
    const title = str(v.title);
    const hit = orgStore().positions.find((x) => !x.archived && x.title === title && x.department_id === dept?.id);
    if (hit) return ref("hr", "positions", hit.id, hit.version, true);
    const row: MPosition = { id: newCaptureId("position"), version: 1, department_id: dept?.id ?? "", code: `POS-${orgStore().positions.length + 1}`, title, level: null, headcount_budget: 0,
      reports_to_position_id: null, archived: false, created_at: at, updated_at: at };
    orgStore().positions.push(row);
    lineage(d, action, r, "hr.positions", row.id, at);
    return ref("hr", "positions", row.id, 1);
  }
  if (action === "ACT-create_employee") {
    const e: MEmployee = { id: newCaptureId("employee"), code: str(v.employee_code), full_name: str(v.full_name), version: 1, deleted: false };
    orgStore().employees.push(e);
    const dept = liveDept(str(v.department_code));
    if (dept) orgStore().assignments.push({ id: newCaptureId("assignment"), version: 1, employee_id: e.id, department_id: dept.id, team_id: null, position_id: null, manager_id: null,
      valid_from: str(v.hire_date) || today(), valid_to: null, reason: null, created_at: at, updated_at: at });
    lineage(d, action, r, "hr.employees", e.id, at);
    return ref("hr", "employees", e.id, 1);
  }
  if (action === "ACT-create_task") {
    const me = employeeOf(c);
    const t = task({ id: newCaptureId("task"), title: str(v.task_title), due_date: str(v.task_due_date) || null, owner_id: c.sub, assignee_id: me ?? null,
      department_id: c.department_id, source: sourceOf(d), task_source: "document", source_document_id: d.id, source_ref: { kind: "document", id: d.id, page: null }, created_at: at, updated_at: at });
    workStore().tasks.push(t);
    lineage(d, action, r, "execution.tasks", t.id, at);
    return ref("execution", "tasks", t.id, 1);
  }
  if (action === "ACT-upsert_kpi") {
    const code = str(v.kpi_code);
    const hit = goalStore().kpis.find((k) => !k.deleted && k.code === code);
    const target = Number(v.target ?? v.kpi_period_target ?? 0);
    if (hit) {
      const out = { ...ref("execution", "kpis", hit.id, hit.version + 1), snapshot: { version: hit.version + 1, target: hit.target, updated: true } };
      Object.assign(hit, { target, version: hit.version + 1, updated_at: at });
      lineage(d, action, r, "execution.kpis", hit.id, at);
      return out;
    }
    const k: MKpi = { ...goalBase(newCaptureId("kpi"), at), source: sourceOf(d), code, name: str(v.kpi_name) || code, unit: str(v.unit), target, owner_id: c.sub, metric_code: null, key_result_id: null,
      period_type: "QUARTER", direction: "HIGHER_IS_BETTER", value_type: "numeric", data_source_kind: "manual", parent_kpi_id: null, weight_pct: 100, initiative_id: null,
      department_id: c.department_id, status: "active", strategic_objective_id: null, pillar: null };
    goalStore().kpis.push(k);
    lineage(d, action, r, "execution.kpis", k.id, at);
    return ref("execution", "kpis", k.id, 1);
  }
  // Targets without a mock store (objectives, key results, KPI targets, measurements, invoices): id + lineage only.
  const [schema = "execution", table = "records"] = (ACT_TABLE[action] ?? "execution.records").split(".");
  const id = mockId("record", `${d.id}:${action}:${r.row_index ?? "h"}`);
  lineage(d, action, r, `${schema}.${table}`, id, at);
  return ref(schema, table, id, 1);
}

function current(r: MResultRef): { version: number } | undefined {
  if (r.table === "departments") return orgStore().depts.find((x) => x.id === r.id);
  if (r.table === "employees") return orgStore().employees.find((x) => x.id === r.id);
  if (r.table === "positions") return orgStore().positions.find((x) => x.id === r.id);
  if (r.table === "tasks") return workStore().tasks.find((x) => x.id === r.id);
  if (r.table === "kpis") return goalStore().kpis.find((x) => x.id === r.id);
  return undefined;
}

/** True when the target row moved past the version written by the ACT. */
export function refEdited(r: MResultRef): boolean {
  const row = current(r);
  return row !== undefined && row.version !== Number(r.snapshot?.version ?? row.version);
}

export function undoRef(r: MResultRef): void {
  const at = new Date().toISOString();
  if (r.table === "departments") Object.assign(orgStore().depts.find((x) => x.id === r.id) ?? {}, { archived: true, valid_to: today(), updated_at: at });
  if (r.table === "positions") Object.assign(orgStore().positions.find((x) => x.id === r.id) ?? {}, { archived: true, updated_at: at });
  if (r.table === "employees") {
    Object.assign(orgStore().employees.find((x) => x.id === r.id) ?? {}, { deleted: true });
    for (const a of orgStore().assignments) if (a.employee_id === r.id && a.valid_to === null) a.valid_to = today();
  }
  if (r.table === "tasks") Object.assign(workStore().tasks.find((x) => x.id === r.id) ?? {}, { deleted: true, updated_at: at });
  if (r.table === "kpis") {
    const k = goalStore().kpis.find((x) => x.id === r.id);
    if (k && r.snapshot?.updated) Object.assign(k, { target: r.snapshot.target, version: k.version + 1, updated_at: at });
    else if (k) Object.assign(k, { deleted: true, updated_at: at });
  }
}

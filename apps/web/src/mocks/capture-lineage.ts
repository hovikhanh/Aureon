/**
 * Mock EP-DC-26 `GET /lineage/{entity}/{id}` (FR-DATA-04, R-DEC-64): entity whitelist (else 422),
 * two-sided scope — target record readable by the caller AND every source document visible —
 * otherwise `200 {restricted:true, reason}`; level-4 `raw_text` → `{masked:true}`.
 */
import type { MockClaims } from "./fixtures";
import { ok } from "./http";
import type { MockRequest } from "./router";
import { orgStore } from "./org";
import { workStore } from "./work-store";
import { taskVisible } from "./work";
import { goalStore } from "./goals-store";
import { canRead } from "./goal-scope";
import { docVisible, seesLevel4 } from "./capture-scope";
import { captureStore } from "./capture-store";
import { err } from "./capture-out";

export const LINEAGE_ENTITIES = ["hr.departments", "hr.teams", "hr.positions", "hr.employees", "execution.tasks", "execution.kpis", "execution.kpi_targets",
  "execution.kpi_measurements", "execution.objectives", "execution.key_results", "execution.check_ins", "finance.invoices"] as const;

function departmentOf(entity: string, id: string): string | null {
  if (entity === "hr.departments") return id;
  if (entity === "hr.employees") return orgStore().assignments.find((a) => a.employee_id === id && a.valid_to === null)?.department_id ?? null;
  return null;
}

function targetVisible(c: MockClaims, entity: string, id: string): boolean {
  if (c.role === "CEO") return true;
  if (c.role === "ADM" || c.role === "AI") return false;
  const [schema] = entity.split(".");
  if (schema === "hr") {
    if (c.role === "DIR") return c.scope_pillars.length === 0 || c.scope_pillars.includes("O");
    if (c.role === "MGR") return departmentOf(entity, id) === c.department_id;
    if (c.role === "EMP") return entity === "hr.employees" && id === c.employee_id;
    return c.role === "REV";
  }
  if (entity === "execution.tasks") {
    const t = workStore().tasks.find((x) => x.id === id && !x.deleted);
    return t ? taskVisible(c, t) : true;
  }
  if (entity === "execution.kpis") {
    const k = goalStore().kpis.find((x) => x.id === id);
    return k ? canRead(c, k) : true;
  }
  if (schema === "finance") return c.permissions.includes("finance:read") && (c.role !== "DIR" || c.scope_pillars.length === 0 || c.scope_pillars.includes("F"));
  return c.role !== "EMP";
}

export function lineage(req: MockRequest): Response {
  const c = req.claims;
  const entity = req.params.entity ?? "";
  const id = req.params.id ?? "";
  if (!(LINEAGE_ENTITIES as readonly string[]).includes(entity)) throw err(422, "VALIDATION_ERROR", "unknown lineage entity", { field: "entity", allowed: LINEAGE_ENTITIES.join(",") });
  if (!targetVisible(c, entity, id)) return ok({ restricted: true, reason: "target_out_of_scope" });
  const s = captureStore();
  const rows = s.lineage.filter((l) => l.entity === entity && l.record_id === id);
  const docs = rows.map((l) => s.docs.find((d) => d.id === l.document_id)).filter((d) => d !== undefined);
  if (docs.some((d) => !docVisible(c, d))) return ok({ restricted: true, reason: "source_out_of_scope" });
  const links = rows.map((l) => {
    const d = docs.find((x) => x.id === l.document_id)!;
    return { target_column: l.target_column, source_document_id: d.id, document_type: d.document_type, original_filename: d.original_filename, page_number: d.kind === "MANUAL" ? null : 1,
      sheet_name: d.sheet_name, row_index: l.row_index, field_name: l.field_name, raw_text: l.sensitivity_level >= 4 && !seesLevel4(c, d) ? { masked: true } : l.raw_text,
      confidence: l.confidence, action_name: l.action_name, committed_at: l.committed_at, revoked_at: l.revoked_at };
  });
  return ok({ entity, id, links, restricted: false, reason: null });
}

/**
 * Mock of `execution/services/goal_scope.py` (R-DEC-57, 10 §7.2.3 "Quyền & data scope"):
 * CEO all · DIR khối = own department subtree ∪ `pillar ∈ scope_pillars` ∪ own rows ∪ company
 * rows (read only; empty `scope_pillars` → all) · MGR = own department + sub-departments ∪ own
 * rows ∪ company rows (read only) · EMP = own rows (`owner_id = user_id`) + ancestors as
 * `restricted` nodes. GET detail outside scope → 403 FORBIDDEN_SCOPE; lists drop the row.
 */
import type { MockClaims } from "./fixtures";
import { MockHttpError } from "./http";
import { orgStore } from "./org";

export interface Scoped { department_id: string | null; pillar: string | null; owner_id: string }

/** `core/org_scope.department_subtree()` — department + every descendant. */
export function departmentSubtree(root: string): Set<string> {
  const out = new Set([root]);
  let grew = true;
  while (grew) {
    grew = false;
    for (const d of orgStore().depts) if (d.parent_id && out.has(d.parent_id) && !out.has(d.id)) { out.add(d.id); grew = true; }
  }
  return out;
}

const dirAll = (c: MockClaims) => c.role === "DIR" && c.scope_pillars.length === 0;

function inUnit(c: MockClaims, r: Scoped): boolean {
  if (r.department_id !== null && departmentSubtree(c.department_id).has(r.department_id)) return true;
  return c.role === "DIR" && r.pillar !== null && c.scope_pillars.includes(r.pillar);
}

export function canRead(c: MockClaims, r: Scoped): boolean {
  if (c.role === "CEO" || dirAll(c)) return true;
  if (r.owner_id === c.sub) return true;
  if (c.role === "EMP") return false;
  if (c.role !== "DIR" && c.role !== "MGR") return false;
  return r.department_id === null || inUnit(c, r);
}

/** Write KPI / Objective / KR / Initiative / check-in on behalf (not EMP — EMP check-in: see `canCheckIn`). */
export function canWrite(c: MockClaims, r: Scoped): boolean {
  if (c.role === "CEO" || dirAll(c)) return true;
  if (c.role !== "DIR" && c.role !== "MGR") return false;
  return r.owner_id === c.sub || inUnit(c, r);
}

export function canCheckIn(c: MockClaims, r: Scoped): boolean {
  return c.role === "EMP" ? r.owner_id === c.sub : canWrite(c, r);
}

export const forbiddenScope = (what: string, details: Record<string, unknown> = {}) => new MockHttpError(403, "FORBIDDEN_SCOPE", `${what} outside your scope`, details);
export const forbiddenRole = (what: string) => new MockHttpError(403, "FORBIDDEN_ROLE", `role may not ${what}`, {});

/** EMP may not create/edit KPI / Objective / KR / Initiative (→ 403 FORBIDDEN_ROLE). */
export function requireManager(c: MockClaims, what: string): void {
  if (c.role !== "CEO" && c.role !== "DIR" && c.role !== "MGR") throw forbiddenRole(what);
}

/** `pin_department`: MGR/DIR create inside their subtree (DIR also by pillar); default = own department. */
export function pinDepartment(c: MockClaims, requested: string | null | undefined, pillar: string | null | undefined): string | null {
  if (c.role === "CEO" || dirAll(c)) return requested ?? null;
  const dept = requested ?? c.department_id;
  if (!inUnit(c, { department_id: dept, pillar: pillar ?? null, owner_id: "" })) throw forbiddenScope("department", { field: "department_id" });
  return dept;
}

/** Strategy: CEO only. StrategicObjective: CEO, DIR inside `scope_pillars`. */
export function requireStrategyWrite(c: MockClaims): void {
  if (c.role !== "CEO") throw forbiddenRole("write strategies");
}
export function requireSoWrite(c: MockClaims, pillar: string | null | undefined): void {
  if (c.role === "CEO") return;
  if (c.role !== "DIR") throw forbiddenRole("write strategic objectives");
  if (c.scope_pillars.length && !(pillar && c.scope_pillars.includes(pillar))) throw forbiddenScope("pillar", { field: "pillar" });
}

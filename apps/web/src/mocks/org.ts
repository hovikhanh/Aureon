/**
 * Mock org structure (T-617F, EP-ORG-01..24 + EP-81 departments) — one shared in-memory store
 * seeded from `seed_snapshot.json` (organization, departments, teams, assignments incl. the
 * T-617 transfer history), so an ADM edit is seen by the CEO in the same mock process.
 * Mirrors the backend rules the UI relies on: effective-dated `as_of`, archive blocked with
 * `422 details.reason=has_live_children`, MGR pinned to the own department, EMP/REV → 403.
 */
import { SNAPSHOT, mockId, type MockClaims } from "./fixtures";
import { MockHttpError, ok, paginate, parsePage } from "./http";
import { recordAudit } from "./audit";
import type { MockRequest, Route } from "./router";

export interface MDept { id: string; version: number; organization_id: string; code: string; name: string; parent_id: string | null; manager_id: string | null; valid_from: string; valid_to: string | null; archived: boolean; created_at: string; updated_at: string }
export interface MTeam { id: string; version: number; department_id: string; code: string; name: string; lead_employee_id: string | null; valid_from: string; valid_to: string | null; archived: boolean; created_at: string; updated_at: string }
export interface MPosition { id: string; version: number; department_id: string; code: string; title: string; level: number | null; headcount_budget: number; reports_to_position_id: string | null; archived: boolean; created_at: string; updated_at: string }
export interface MAssignment { id: string; version: number; employee_id: string; department_id: string; team_id: string | null; position_id: string | null; manager_id: string | null; valid_from: string; valid_to: string | null; reason: string | null; created_at: string; updated_at: string }

const STAMP = `${SNAPSHOT.reference_date}T01:00:00Z`;
const ORG = SNAPSHOT.organization;
export const ORG_ID = mockId("organization", ORG.code);
const dId = (code: string) => mockId("department", code);
const tId = (code: string) => mockId("team", code);
export const eId = (code: string) => mockId("employee", code);
const EMP = new Map(SNAPSHOT.employees.map((e) => [eId(e.code), e]));
/** Employees created at runtime (M1.5 ACT-create_employee via the capture mock). */
export interface MEmployee { id: string; code: string; full_name: string; version: number; deleted: boolean }
const empOf = (id: string) => EMP.get(id) ?? orgStore().employees.find((e) => e.id === id && !e.deleted);

interface OrgStore { depts: MDept[]; teams: MTeam[]; positions: MPosition[]; assignments: MAssignment[]; employees: MEmployee[]; seq: number }
// on globalThis: `next dev` re-evaluates server modules when it compiles another page
const G = globalThis as typeof globalThis & { __aureonMockOrg?: OrgStore | null };

function seed(): OrgStore {
  const base = { version: 1, valid_from: ORG.valid_from, valid_to: null, archived: false, created_at: STAMP, updated_at: STAMP };
  return {
    depts: SNAPSHOT.departments.map((d) => ({ ...base, id: dId(d.code), organization_id: ORG_ID, code: d.code, name: d.name, parent_id: null, manager_id: eId(d.head) })),
    teams: SNAPSHOT.departments.flatMap((d) => d.teams.map((t) => ({ ...base, id: tId(t.code), department_id: dId(d.code), code: t.code, name: t.name, lead_employee_id: null }))),
    positions: [],
    employees: [],
    assignments: SNAPSHOT.assignments.map((a, i) => ({
      id: mockId("assignment", `${a.employee}:${i}`), version: 1, employee_id: eId(a.employee), department_id: dId(a.department),
      team_id: a.team ? tId(a.team) : null, position_id: null, manager_id: a.manager ? eId(a.manager) : null,
      valid_from: a.valid_from, valid_to: a.valid_to, reason: null, created_at: STAMP, updated_at: STAMP,
    })),
    seq: 0,
  };
}

export function orgStore(): OrgStore {
  G.__aureonMockOrg ??= seed();
  return G.__aureonMockOrg;
}

export function resetOrgStore(): void {
  G.__aureonMockOrg = null;
}

export const today = (): string => new Date().toISOString().slice(0, 10);
const now = (): string => new Date().toISOString();
const newId = (kind: string): string => mockId(kind, `new-${++orgStore().seq}-${Date.now()}`);
const live = (from: string, to: string | null, at: string) => from <= at && (to === null || to > at);

function asOf(q: URLSearchParams): string {
  const v = q.get("as_of");
  if (v === null || v === "") return today();
  if (!/^\d{4}-\d{2}-\d{2}$/.test(v) || Number.isNaN(Date.parse(v))) throw new MockHttpError(400, "BAD_REQUEST", "as_of must be YYYY-MM-DD", { param: "as_of" });
  return v;
}

/** `null` = whole organization; a set = MGR's own department subtree (EP-ORG reads). */
function visible(c: MockClaims): Set<string> | null {
  if (c.role === "EMP" || c.role === "REV" || c.role === "AI") throw new MockHttpError(403, "FORBIDDEN_SCOPE", "org structure outside scope", { role: c.role });
  if (c.role !== "MGR") return null;
  const out = new Set([c.department_id]);
  let grew = true;
  while (grew) {
    grew = false;
    for (const d of orgStore().depts) if (d.parent_id && out.has(d.parent_id) && !out.has(d.id)) { out.add(d.id); grew = true; }
  }
  return out;
}

function body<T>(req: MockRequest): Partial<T> {
  return (req.body && typeof req.body === "object" ? req.body : {}) as Partial<T>;
}

function required(b: Record<string, unknown>, ...fields: string[]): void {
  const missing = fields.filter((f) => b[f] === undefined || b[f] === null || b[f] === "");
  if (missing.length) throw new MockHttpError(422, "VALIDATION_ERROR", "invalid body", { fields: missing });
}

function rule(message: string, reason: string, extra: Record<string, unknown> = {}): never {
  throw new MockHttpError(422, "BUSINESS_RULE_VIOLATION", message, { reason, ...extra });
}

function versionCheck(row: { version: number }, b: { version?: number | null }): void {
  if (b.version != null && b.version !== row.version) throw new MockHttpError(409, "CONFLICT_STATE", "stale version", { expected: row.version });
}

function idem(req: MockRequest): void {
  if (!req.headers.get("idempotency-key")?.trim()) throw new MockHttpError(400, "BAD_REQUEST", "Idempotency-Key header is required", { header: "Idempotency-Key" });
}

function strip<T extends { archived: boolean }>(row: T): Omit<T, "archived"> {
  const out: Partial<T> = { ...row };
  delete out.archived;
  return out as Omit<T, "archived">;
}
const deptOut = (d: MDept) => strip(d);
const teamOut = (t: MTeam) => strip(t);
function positionOut(row: MPosition) {
  const p = strip(row);
  const filled = orgStore().assignments.filter((a) => a.position_id === p.id && a.valid_to === null).length;
  return { ...p, filled, vacant: Math.max(0, p.headcount_budget - filled) };
}

function findOr404<T extends { id: string }>(rows: T[], id: string | undefined, what: string): T {
  const row = rows.find((r) => r.id === id);
  if (!row) throw new MockHttpError(404, "NOT_FOUND", `${what} not found`);
  return row;
}

function tree(req: MockRequest) {
  const at = asOf(req.query);
  const seen = visible(req.claims);
  const s = orgStore();
  const depts = s.depts.filter((d) => live(d.valid_from, d.valid_to, at) && (seen === null || seen.has(d.id)));
  const ids = new Set(depts.map((d) => d.id));
  const current = s.assignments.filter((a) => ids.has(a.department_id) && live(a.valid_from, a.valid_to, at) && empOf(a.employee_id) !== undefined);
  const title = (pid: string | null) => s.positions.find((p) => p.id === pid)?.title ?? null;
  return ok({
    as_of: at,
    organization: { id: ORG_ID, code: ORG.code, name: ORG.name },
    departments: depts.map((d) => {
      const members = current.filter((a) => a.department_id === d.id).map((a) => {
        const e = empOf(a.employee_id)!;
        return { employee_id: a.employee_id, employee_code: e.code, full_name: e.full_name, team_id: a.team_id, position_id: a.position_id, position_title: title(a.position_id), manager_id: a.manager_id };
      });
      const teams = s.teams.filter((t) => t.department_id === d.id && live(t.valid_from, t.valid_to, at))
        .map((t) => ({ id: t.id, code: t.code, name: t.name, lead_employee_id: t.lead_employee_id, headcount: members.filter((m) => m.team_id === t.id).length }));
      return { id: d.id, code: d.code, name: d.name, parent_id: d.parent_id, manager_id: d.manager_id, headcount: members.length, teams, members };
    }),
  });
}

function createDept(req: MockRequest) {
  idem(req);
  const b = body<MDept>(req);
  required(b, "name", "code", "organization_id");
  const s = orgStore();
  if (b.organization_id !== ORG_ID) rule("organization not found", "not_found", { field: "organization_id" });
  if (s.depts.some((d) => !d.archived && d.code === b.code)) throw new MockHttpError(409, "DUPLICATE_RESOURCE", "department code exists", { field: "code" });
  if (b.parent_id) findOr404(s.depts.filter((d) => !d.archived), b.parent_id, "parent department");
  const row: MDept = { id: newId("department"), version: 1, organization_id: ORG_ID, code: String(b.code), name: String(b.name), parent_id: b.parent_id ?? null,
    manager_id: b.manager_id ?? null, valid_from: b.valid_from ?? today(), valid_to: null, archived: false, created_at: now(), updated_at: now() };
  s.depts.push(row);
  recordAudit(req.claims, "hr.department_create", "departments", row.id);
  return ok(deptOut(row), 201);
}

function patchDept(req: MockRequest) {
  const s = orgStore();
  const row = findOr404(s.depts.filter((d) => !d.archived), req.params.id, "department");
  const b = body<MDept>(req);
  versionCheck(row, b);
  if (b.parent_id) {
    let cur: string | null = b.parent_id;
    while (cur) {
      if (cur === row.id) rule("parent would create a cycle", "parent_cycle", { field: "parent_id" });
      cur = s.depts.find((d) => d.id === cur)?.parent_id ?? null;
    }
  }
  if (b.code && s.depts.some((d) => !d.archived && d.code === b.code && d.id !== row.id)) throw new MockHttpError(409, "DUPLICATE_RESOURCE", "department code exists", { field: "code" });
  Object.assign(row, Object.fromEntries(Object.entries(b).filter(([k]) => ["name", "code", "parent_id", "manager_id"].includes(k))));
  row.version += 1;
  row.updated_at = now();
  recordAudit(req.claims, "hr.department_update", "departments", row.id);
  return ok(deptOut(row));
}

function archiveDept(req: MockRequest) {
  const s = orgStore();
  const row = findOr404(s.depts.filter((d) => !d.archived), req.params.id, "department");
  const children = s.depts.filter((d) => !d.archived && d.parent_id === row.id).length + s.teams.filter((t) => !t.archived && t.department_id === row.id).length;
  const assignments = s.assignments.filter((a) => a.department_id === row.id && a.valid_to === null).length;
  if (children || assignments) rule("department still has live children", "has_live_children", { children, assignments });
  Object.assign(row, { archived: true, valid_to: today(), updated_at: now() });
  recordAudit(req.claims, "hr.department_archive", "departments", row.id);
  return ok(null, 204);
}

function createTeam(req: MockRequest) {
  idem(req);
  const b = body<MTeam>(req);
  required(b, "department_id", "code", "name");
  const s = orgStore();
  findOr404(s.depts.filter((d) => !d.archived), b.department_id, "department");
  if (s.teams.some((t) => !t.archived && t.code === b.code)) throw new MockHttpError(409, "DUPLICATE_RESOURCE", "team code exists", { field: "code" });
  const row: MTeam = { id: newId("team"), version: 1, department_id: String(b.department_id), code: String(b.code), name: String(b.name), lead_employee_id: b.lead_employee_id ?? null,
    valid_from: b.valid_from ?? today(), valid_to: null, archived: false, created_at: now(), updated_at: now() };
  s.teams.push(row);
  recordAudit(req.claims, "hr.team_create", "teams", row.id);
  return ok(teamOut(row), 201);
}

function patchTeam(req: MockRequest) {
  const row = findOr404(orgStore().teams.filter((t) => !t.archived), req.params.id, "team");
  const b = body<MTeam>(req);
  versionCheck(row, b);
  Object.assign(row, Object.fromEntries(Object.entries(b).filter(([k]) => ["name", "code", "lead_employee_id"].includes(k))));
  row.version += 1;
  row.updated_at = now();
  recordAudit(req.claims, "hr.team_update", "teams", row.id);
  return ok(teamOut(row));
}

function archiveTeam(req: MockRequest) {
  const s = orgStore();
  const row = findOr404(s.teams.filter((t) => !t.archived), req.params.id, "team");
  const assignments = s.assignments.filter((a) => a.team_id === row.id && a.valid_to === null).length;
  if (assignments) rule("team still has current assignments", "has_live_children", { assignments });
  Object.assign(row, { archived: true, valid_to: today(), updated_at: now() });
  recordAudit(req.claims, "hr.team_archive", "teams", row.id);
  return ok(null, 204);
}

function listPositions(req: MockRequest) {
  visible(req.claims);
  const dept = req.query.get("department_id");
  const q = req.query.get("q")?.toLowerCase();
  const rows = orgStore().positions.filter((p) => !p.archived && (!dept || p.department_id === dept) && (!q || `${p.code} ${p.title}`.toLowerCase().includes(q)));
  return paginate(rows.map(positionOut), parsePage(req.query, ["code", "title"]));
}

function createPosition(req: MockRequest) {
  idem(req);
  const b = body<MPosition>(req);
  required(b, "department_id", "code", "title", "headcount_budget");
  const s = orgStore();
  findOr404(s.depts.filter((d) => !d.archived), b.department_id, "department");
  if (s.positions.some((p) => !p.archived && p.code === b.code)) throw new MockHttpError(409, "DUPLICATE_RESOURCE", "position code exists", { field: "code" });
  const row: MPosition = { id: newId("position"), version: 1, department_id: String(b.department_id), code: String(b.code), title: String(b.title), level: b.level ?? null,
    headcount_budget: Number(b.headcount_budget), reports_to_position_id: b.reports_to_position_id ?? null, archived: false, created_at: now(), updated_at: now() };
  s.positions.push(row);
  recordAudit(req.claims, "hr.position_create", "positions", row.id);
  return ok(positionOut(row), 201);
}

function patchPosition(req: MockRequest) {
  const row = findOr404(orgStore().positions.filter((p) => !p.archived), req.params.id, "position");
  const b = body<MPosition>(req);
  versionCheck(row, b);
  if (b.reports_to_position_id === row.id) rule("position cannot report to itself", "parent_cycle", { field: "reports_to_position_id" });
  Object.assign(row, Object.fromEntries(Object.entries(b).filter(([k]) => ["title", "level", "headcount_budget", "reports_to_position_id"].includes(k))));
  row.version += 1;
  row.updated_at = now();
  recordAudit(req.claims, "hr.position_update", "positions", row.id);
  return ok(positionOut(row));
}

function listAssignments(req: MockRequest) {
  const seen = visible(req.claims);
  const emp = req.query.get("employee_id");
  const dept = req.query.get("department_id");
  const at = req.query.get("as_of");
  const rows = orgStore().assignments
    .filter((a) => (!emp || a.employee_id === emp) && (!dept || a.department_id === dept) && (!at || live(a.valid_from, a.valid_to, at)) && (seen === null || seen.has(a.department_id)))
    .sort((a, b) => a.valid_from.localeCompare(b.valid_from));
  return paginate(rows as unknown as Record<string, unknown>[], parsePage(req.query, ["valid_from"]));
}

function createAssignment(req: MockRequest) {
  idem(req);
  const b = body<MAssignment>(req);
  required(b, "employee_id", "department_id", "valid_from");
  const s = orgStore();
  if (!empOf(String(b.employee_id))) rule("employee not found", "not_found", { field: "employee_id" });
  findOr404(s.depts.filter((d) => !d.archived), b.department_id, "department");
  if (b.team_id && s.teams.find((t) => t.id === b.team_id)?.department_id !== b.department_id) rule("team not in department", "team_outside_department", { field: "team_id" });
  if (b.manager_id && b.manager_id === b.employee_id) rule("employee cannot manage themself", "manager_self", { field: "manager_id" });
  const from = String(b.valid_from);
  if (from > today()) rule("valid_from cannot be in the future", "future", { field: "valid_from" });
  const current = s.assignments.find((a) => a.employee_id === b.employee_id && a.valid_to === null);
  if (current && from <= current.valid_from) rule("valid_from must be after the current assignment start", "not_after_current", { field: "valid_from" });
  if (current) Object.assign(current, { valid_to: from, version: current.version + 1, updated_at: now() });
  const row: MAssignment = { id: newId("assignment"), version: 1, employee_id: String(b.employee_id), department_id: String(b.department_id), team_id: b.team_id ?? null,
    position_id: b.position_id ?? null, manager_id: b.manager_id ?? null, valid_from: from, valid_to: null, reason: b.reason ?? null, created_at: now(), updated_at: now() };
  s.assignments.push(row);
  recordAudit(req.claims, "hr.assignment_create", "employee_assignments", row.id);
  return ok(row, 201);
}

const list = <T extends { archived: boolean }>(rows: T[], map: (r: T) => object) => (req: MockRequest) => {
  visible(req.claims);
  return paginate(rows.filter((r) => !r.archived).map(map) as Record<string, unknown>[], parsePage(req.query, ["name", "code"]));
};

export const ORG_ROUTES: readonly Route[] = [
  { method: "GET", pattern: "/org/tree", permission: "hr:read", handler: tree },
  { method: "GET", pattern: "/org/organizations", permission: "hr:read", handler: (req) => { visible(req.claims); return ok([{ id: ORG_ID, code: ORG.code, name: ORG.name, legal_name: ORG.name, tax_code: null, valid_from: ORG.valid_from, valid_to: null, version: 1, created_at: STAMP, updated_at: STAMP }], 200, { pagination: { total: 1, limit: 20, offset: 0, has_next: false } }); } },
  { method: "GET", pattern: "/hr/departments", permission: "hr:read", handler: (req) => list(orgStore().depts, deptOut)(req) },
  { method: "POST", pattern: "/hr/departments", permission: "hr:admin", handler: createDept },
  { method: "PATCH", pattern: "/hr/departments/:id", permission: "hr:admin", handler: patchDept },
  { method: "DELETE", pattern: "/hr/departments/:id", permission: "hr:admin", handler: archiveDept },
  { method: "GET", pattern: "/org/teams", permission: "hr:read", handler: (req) => list(orgStore().teams.filter((t) => !req.query.get("department_id") || t.department_id === req.query.get("department_id")), teamOut)(req) },
  { method: "POST", pattern: "/org/teams", permission: "hr:admin", handler: createTeam },
  { method: "PATCH", pattern: "/org/teams/:id", permission: "hr:admin", handler: patchTeam },
  { method: "DELETE", pattern: "/org/teams/:id", permission: "hr:admin", handler: archiveTeam },
  { method: "GET", pattern: "/org/positions", permission: "hr:read", handler: listPositions },
  { method: "POST", pattern: "/org/positions", permission: "hr:admin", handler: createPosition },
  { method: "PATCH", pattern: "/org/positions/:id", permission: "hr:admin", handler: patchPosition },
  { method: "GET", pattern: "/org/assignments", permission: "hr:read", handler: listAssignments },
  { method: "POST", pattern: "/org/assignments", permission: "hr:admin", handler: createAssignment },
];


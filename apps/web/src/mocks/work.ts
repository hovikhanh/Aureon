/**
 * Mock `/work/*` (T-625F, 10 §7.2.2 EP-TASK-01..18) on the shared `work-store`. Same rules as the
 * backend spec: data scope DEC-220 (CEO all · DIR/MGR own department + own rows · EMP own rows,
 * "own" = employee_id or user_id — R-DEC-41); read outside scope → 404, write → 403
 * FORBIDDEN_SCOPE; DEC-147 transitions → 409; `done` with open dependencies → 422
 * `details.rule=FR-TASK-02`; `version` mismatch → 409; POST needs `Idempotency-Key`.
 */
import { claimsFor, type MockClaims } from "./fixtures";
import { MockHttpError, ok, paginate, parsePage } from "./http";
import { recordAudit } from "./audit";
import { pushNotification } from "./admin";
import type { MockRequest, Route } from "./router";
import {
  departmentOfEmployee, newWorkId, selfIds, userOfEmployee, workStore, workToday,
  type MDependency, type MTask, type TaskStatus,
} from "./work-store";
import { createReassignRequest } from "./workflow";

export const STATUSES: readonly TaskStatus[] = ["backlog", "todo", "in_progress", "blocked", "in_review", "done", "cancelled"];
const OPEN = new Set<TaskStatus>(["backlog", "todo", "in_progress", "blocked", "in_review"]);
/** DEC-147 (`task_rules.TRANSITIONS`). */
export const TRANSITIONS: Record<TaskStatus, readonly TaskStatus[]> = {
  backlog: ["todo", "in_progress", "blocked", "cancelled"],
  todo: ["backlog", "in_progress", "blocked", "done", "cancelled"],
  in_progress: ["todo", "blocked", "in_review", "done", "cancelled"],
  blocked: ["todo", "in_progress", "cancelled"],
  in_review: ["in_progress", "blocked", "done", "cancelled"],
  done: ["in_progress"],
  cancelled: ["backlog", "todo"],
};
const PRIORITIES = ["low", "medium", "high", "urgent"];
const SOURCE_KINDS = ["meeting", "decision", "ai_action", "document", "mitigation"];

export const err = (status: number, code: string, message: string, details: Record<string, unknown> = {}) => new MockHttpError(status, code, message, details);
export const biz = (message: string, details: Record<string, unknown>) => err(422, "BUSINESS_RULE_VIOLATION", message, details);
export function requireIdem(req: MockRequest): void {
  if (!req.headers.get("idempotency-key")?.trim()) throw err(400, "BAD_REQUEST", "Idempotency-Key header is required", { header: "Idempotency-Key" });
}
export const isDate = (v: unknown): v is string => typeof v === "string" && /^\d{4}-\d{2}-\d{2}$/.test(v) && !Number.isNaN(Date.parse(v));
const body = (req: MockRequest) => (req.body && typeof req.body === "object" ? (req.body as Record<string, unknown>) : {});
const nowIso = () => new Date().toISOString();

// ---------------------------------------------------------------- scope (execution/services/scope.py)
export type Level = "all" | "d" | "o";
export function level(c: MockClaims, action: "read" | "write" | "query" = "read"): Level {
  if (c.role === "EMP") return "o";
  if (action === "query" && (c.role === "CEO" || c.role === "DIR")) return "all";
  if (c.role === "DIR" || c.role === "MGR") return "d";
  return "all";
}
export function allowed(c: MockClaims, action: "read" | "write", dept: string | null, owners: readonly (string | null)[]): boolean {
  const lvl = level(c, action);
  if (lvl === "all") return true;
  const me = selfIds(c);
  if (owners.some((o) => o !== null && me.has(o))) return true;
  return lvl === "d" && dept !== null && dept === c.department_id;
}
export const taskVisible = (c: MockClaims, t: MTask, action: "read" | "write" = "read") => allowed(c, action, t.department_id, [t.owner_id, t.assignee_id]);

export function liveTask(id: string): MTask | undefined {
  return workStore().tasks.find((t) => t.id === id && !t.deleted);
}
/** Read by id: missing / other tenant / outside scope → 404; write outside scope → 403. */
export function getTask(c: MockClaims, id: string, action: "read" | "write" = "read"): MTask {
  const t = liveTask(id);
  if (!t || !taskVisible(c, t, "read")) throw err(404, "NOT_FOUND", "task not found");
  if (action === "write" && !taskVisible(c, t, "write")) throw err(403, "FORBIDDEN_SCOPE", "task outside your scope", { department_id: String(t.department_id) });
  return t;
}

const liveDeps = () => workStore().deps.filter((d) => !d.deleted);
export const isOverdue = (t: Pick<MTask, "status" | "due_date">, today = workToday()) => t.due_date !== null && OPEN.has(t.status) && t.due_date < today;
export function openBlockers(t: MTask): MTask[] {
  return liveDeps().filter((d) => d.task_id === t.id).map((d) => liveTask(d.depends_on_task_id)).filter((x): x is MTask => Boolean(x) && x!.status !== "done" && x!.status !== "cancelled");
}

export function taskOut(t: MTask, today = workToday()) {
  const { deleted: _d, ...rest } = t;
  void _d;
  return {
    ...rest, overdue: isOverdue(t, today),
    subtask_count: workStore().tasks.filter((x) => !x.deleted && x.parent_task_id === t.id).length,
    depends_on_open: openBlockers(t).length,
  };
}

// ---------------------------------------------------------------- EP-TASK-01 list
function listTasks(req: MockRequest): Response {
  const q = req.query;
  const page = parsePage(q, ["due_date", "priority", "status", "updated_at", "title"]);
  const statuses = q.getAll("status");
  for (const s of statuses) if (!STATUSES.includes(s as TaskStatus)) throw err(422, "VALIDATION_ERROR", "invalid status", { field: "status" });
  const dueFrom = q.get("due_from");
  const dueTo = q.get("due_to");
  for (const [k, v] of [["due_from", dueFrom], ["due_to", dueTo]] as const) if (v && !isDate(v)) throw err(422, "VALIDATION_ERROR", `${k} must be a date`, { field: k });
  if (dueFrom && dueTo && dueFrom > dueTo) throw err(400, "BAD_REQUEST", "due_from must be on/before due_to", { param: "due_from" });
  const sk = q.get("source_kind");
  if (sk && !SOURCE_KINDS.includes(sk)) throw err(422, "VALIDATION_ERROR", "invalid source_kind", { field: "source_kind" });
  const overdue = q.get("overdue");
  const me = selfIds(req.claims);
  const eq = (field: keyof MTask) => q.get(field as string);
  const today = workToday();
  const rows = workStore().tasks.filter((t) => !t.deleted && taskVisible(req.claims, t)
    && (!statuses.length || statuses.includes(t.status))
    && (q.get("mine") !== "true" || (t.assignee_id !== null && me.has(t.assignee_id)))
    && (["assignee_id", "owner_id", "department_id", "initiative_id", "project_id", "parent_task_id"] as const).every((f) => !eq(f) || t[f] === eq(f))
    && (!dueFrom || (t.due_date !== null && t.due_date >= dueFrom)) && (!dueTo || (t.due_date !== null && t.due_date <= dueTo))
    && (!sk || t.source_ref?.kind === sk)
    && (overdue === null || overdue === "" || (overdue === "true") === isOverdue(t, today)));
  return paginate(rows.map((t) => taskOut(t, today)) as unknown as Record<string, unknown>[], page);
}

// ---------------------------------------------------------------- EP-TASK-02..05
function requireSelf(c: MockClaims, ids: readonly (string | null | undefined)[], field: string): void {
  if (level(c, "write") !== "o") return;
  const me = selfIds(c);
  if (ids.some((i) => i !== null && i !== undefined && !me.has(i))) throw err(403, "FORBIDDEN_SCOPE", `${field} outside your scope`, { field });
}
function pinDepartment(c: MockClaims, requested: string | null | undefined): string | null {
  const lvl = level(c, "write");
  if (lvl === "all") return requested ?? null;
  if (requested && requested !== c.department_id) throw err(403, "FORBIDDEN_SCOPE", "department outside your scope", { department_id: requested });
  return c.department_id;
}
function checkDates(start: string | null, due: string | null): void {
  if (start && due && due < start) throw biz("due_date must be on/after start_date", { field: "due_date", rule: "BR-EXE" });
}
function checkFields(b: Record<string, unknown>, create: boolean): void {
  if (create || "title" in b) {
    if (typeof b.title !== "string" || !b.title.trim() || b.title.length > 500) throw err(422, "VALIDATION_ERROR", "title is required", { field: "title" });
  }
  if (b.priority !== undefined && b.priority !== null && !PRIORITIES.includes(String(b.priority))) throw err(422, "VALIDATION_ERROR", "invalid priority", { field: "priority" });
  if (b.status !== undefined && b.status !== null && !STATUSES.includes(b.status as TaskStatus)) throw err(422, "VALIDATION_ERROR", "invalid status", { field: "status" });
  for (const f of ["start_date", "due_date"]) if (b[f] !== undefined && b[f] !== null && !isDate(b[f])) throw err(422, "VALIDATION_ERROR", `${f} must be a date`, { field: f });
  const sr = b.source_ref as { kind?: string; id?: string } | null | undefined;
  if (sr && (!SOURCE_KINDS.includes(String(sr.kind)) || typeof sr.id !== "string")) throw err(422, "VALIDATION_ERROR", "invalid source_ref", { field: "source_ref" });
}
/** R-DEC-42: parent must exist, not be itself / a descendant, and not already be a sub-task (1 level). */
function checkParent(c: MockClaims, self: string | null, parentId: unknown): void {
  if (parentId === null || parentId === undefined) return;
  const parent = liveTask(String(parentId));
  if (!parent || !taskVisible(c, parent)) throw err(404, "NOT_FOUND", "task not found"); // BE: parent read scope (EP-TASK-03)
  if (parent.id === self || parent.parent_task_id !== null) throw biz("parent must be a top-level task other than itself", { field: "parent_task_id", rule: "R-DEC-42" });
  if (self && workStore().tasks.some((t) => !t.deleted && t.parent_task_id === self)) throw biz("a task with sub-tasks cannot become a sub-task", { field: "parent_task_id", rule: "R-DEC-42" });
}
function notifyAssigned(c: MockClaims, t: MTask): void {
  const u = userOfEmployee(t.assignee_id);
  if (!u || selfIds(c).has(t.assignee_id ?? "")) return;
  pushNotification(claimsFor(u), { kind: "task_assigned", title: t.title, body: "", link: `/work?task=${t.id}`, ref_schema: "execution", ref_table: "tasks", ref_id: t.id });
}

function createTask(req: MockRequest): Response {
  requireIdem(req);
  const c = req.claims;
  const b = body(req);
  checkFields(b, true);
  const owner = (b.owner_id as string | null | undefined) ?? c.sub;
  let assignee = (b.assignee_id as string | null | undefined) ?? null;
  if (level(c, "write") === "o" && assignee === null) assignee = [...selfIds(c)].pop() ?? c.sub;
  requireSelf(c, [owner, assignee], "assignee_id");
  const department = pinDepartment(c, (b.department_id as string | null | undefined) ?? (level(c, "write") === "all" ? departmentOfEmployee(assignee) : null));
  const status = (b.status as TaskStatus | undefined) ?? "todo";
  if (status === "blocked" && !b.blocked_reason) throw biz("blocked requires blocked_reason", { field: "blocked_reason", rule: "DEC-147" });
  checkDates((b.start_date as string | null) ?? null, (b.due_date as string | null) ?? null);
  checkParent(c, null, b.parent_task_id);
  if (b.project_id && !workStore().projects.some((p) => p.id === b.project_id && !p.deleted)) throw biz("project not found", { field: "project_id", rule: "BR-EXE" });
  const stamp = nowIso();
  const t: MTask = {
    id: newWorkId("task"), version: 1, source: "MANUAL", data_classification: "internal", created_at: stamp, updated_at: stamp,
    title: String(b.title).trim(), description: (b.description as string | null) ?? null, owner_id: owner, assignee_id: assignee, department_id: department,
    start_date: (b.start_date as string | null) ?? null, due_date: (b.due_date as string | null) ?? null, priority: (b.priority as string) ?? "medium",
    status, blocked_reason: status === "blocked" ? String(b.blocked_reason) : null, done_at: status === "done" ? stamp : null,
    estimate_hours: b.estimate_hours === undefined || b.estimate_hours === null ? null : Number(b.estimate_hours), actual_hours: null, evidence: null,
    project_id: (b.project_id as string | null) ?? null, initiative_id: null, milestone_id: (b.milestone_id as string | null) ?? null, meeting_id: null,
    decision_id: null, key_result_id: null, kpi_id: null, parent_task_id: (b.parent_task_id as string | null) ?? null,
    source_ref: (b.source_ref as MTask["source_ref"]) ?? null, is_critical: Boolean(b.is_critical), task_source: (b.task_source as string) ?? "manual",
    source_document_id: null, deleted: false,
  };
  workStore().tasks.push(t);
  recordAudit(c, "execution.task_create", "tasks", t.id);
  notifyAssigned(c, t);
  return ok(taskOut(t), 201);
}

/** `core/concurrency.py`: If-Match or body `version` required (else 422); stale → 409. */
export function expectVersion(req: MockRequest, current: number): void {
  const b = body(req);
  const header = req.headers.get("if-match");
  const raw = header ? header.replace(/^W\//, "").replace(/"/g, "") : b.version === undefined || b.version === null ? null : String(b.version);
  if (raw === null || !/^\d+$/.test(raw.trim())) throw err(422, "VALIDATION_ERROR", "PATCH requires the current version", { fields: [{ field: "version", reason: "required" }] });
  if (Number(raw) !== current) throw err(409, "CONFLICT_STATE", "version mismatch", { expected: Number(raw), current });
}

const PATCHABLE = ["title", "description", "owner_id", "assignee_id", "department_id", "start_date", "due_date", "priority", "status", "blocked_reason",
  "estimate_hours", "actual_hours", "project_id", "milestone_id", "parent_task_id", "source_ref", "is_critical"] as const;

function patchTask(req: MockRequest): Response {
  const c = req.claims;
  const t = getTask(c, req.params.id ?? "", "write");
  expectVersion(req, t.version);
  const b = body(req);
  checkFields(b, false);
  requireSelf(c, [b.owner_id as string | undefined, b.assignee_id as string | undefined], "assignee_id");
  const next = { ...t } as Record<string, unknown> & MTask;
  for (const f of PATCHABLE) if (f in b) next[f] = b[f] as never;
  if ("department_id" in b) next.department_id = pinDepartment(c, b.department_id as string | null);
  checkDates(next.start_date, next.due_date);
  if ("parent_task_id" in b) checkParent(c, t.id, b.parent_task_id);
  const status = next.status;
  if (status !== t.status) {
    if (!TRANSITIONS[t.status].includes(status)) throw err(409, "CONFLICT_STATE", `cannot move task from ${t.status} to ${status}`, { from_status: t.status, to_status: status });
    if (status === "done") {
      const open = openBlockers(t);
      if (open.length) throw biz("open dependencies block done", { rule: "FR-TASK-02", blocking: open.map((x) => ({ task_id: x.id, title: x.title, status: x.status })) });
    }
  }
  if (status === "blocked" && !next.blocked_reason) throw biz("blocked requires blocked_reason", { field: "blocked_reason", rule: "DEC-147" });
  if (status !== "blocked" && status !== t.status) next.blocked_reason = null;
  next.done_at = status === "done" ? (t.status === "done" ? t.done_at : nowIso()) : null;
  const reassigned = next.assignee_id !== t.assignee_id;
  Object.assign(t, next, { version: t.version + 1, updated_at: nowIso() });
  recordAudit(c, "execution.task_update", "tasks", t.id);
  if (reassigned) notifyAssigned(c, t);
  return ok(taskOut(t));
}

function deleteTask(req: MockRequest): Response {
  const t = getTask(req.claims, req.params.id ?? "", "write");
  if (workStore().tasks.some((x) => !x.deleted && x.parent_task_id === t.id)) throw biz("task has live sub-tasks", { reason: "has_subtasks", rule: "R-DEC-42" });
  t.deleted = true;
  for (const d of workStore().deps) if (d.task_id === t.id || d.depends_on_task_id === t.id) d.deleted = true;
  recordAudit(req.claims, "execution.task_delete", "tasks", t.id);
  return ok(null, 204);
}

// ---------------------------------------------------------------- EP-TASK-06..08 dependencies
function brief(c: MockClaims, d: MDependency, otherId: string) {
  const o = liveTask(otherId);
  if (!o || !taskVisible(c, o)) return { dependency_id: d.id, task_id: otherId, restricted: true };
  return { dependency_id: d.id, task_id: o.id, title: o.title, status: o.status, due_date: o.due_date, overdue: isOverdue(o), assignee_id: o.assignee_id, restricted: false };
}
function listDeps(req: MockRequest): Response {
  const t = getTask(req.claims, req.params.id ?? "");
  const deps = liveDeps();
  return ok({
    depends_on: deps.filter((d) => d.task_id === t.id).map((d) => brief(req.claims, d, d.depends_on_task_id)),
    blocks: deps.filter((d) => d.depends_on_task_id === t.id).map((d) => brief(req.claims, d, d.task_id)),
  });
}
/** BFS from `target` over depends_on edges; reaching `start` = cycle → `[start, target, …, start]`. */
export function cyclePath(start: string, target: string): string[] | null {
  const edges = liveDeps();
  const prev = new Map<string, string | null>([[target, null]]);
  const queue = [target];
  while (queue.length) {
    const cur = queue.shift() as string;
    if (cur === start) {
      const back: string[] = [];
      for (let p: string | null | undefined = cur; p != null; p = prev.get(p)) back.push(p);
      return [start, ...back.reverse()];
    }
    for (const e of edges) {
      if (e.task_id === cur && !prev.has(e.depends_on_task_id)) { prev.set(e.depends_on_task_id, cur); queue.push(e.depends_on_task_id); }
    }
  }
  return null;
}
function addDep(req: MockRequest): Response {
  requireIdem(req);
  const c = req.claims;
  const t = getTask(c, req.params.id ?? "", "write");
  const b = body(req);
  const target = String(b.depends_on_task_id ?? "");
  if (!target) throw err(422, "VALIDATION_ERROR", "depends_on_task_id is required", { field: "depends_on_task_id" });
  if (b.dependency_type !== undefined && b.dependency_type !== "finish_to_start") throw err(422, "VALIDATION_ERROR", "invalid dependency_type", { field: "dependency_type" });
  const other = liveTask(target);
  if (!other || !taskVisible(c, other)) throw err(404, "NOT_FOUND", "task not found");
  if (other.id === t.id) throw biz("a task cannot depend on itself", { cycle: [t.id, t.id], rule: "FR-TASK-02" });
  if (liveDeps().some((d) => d.task_id === t.id && d.depends_on_task_id === other.id)) throw err(409, "DUPLICATE_RESOURCE", "dependency already exists", { depends_on_task_id: other.id });
  const cycle = cyclePath(t.id, other.id);
  if (cycle) throw biz("dependency would create a cycle", { cycle, rule: "FR-TASK-02" });
  const stamp = nowIso();
  const d: MDependency = { id: newWorkId("dependency"), version: 1, task_id: t.id, depends_on_task_id: other.id, created_at: stamp, deleted: false };
  workStore().deps.push(d);
  recordAudit(c, "execution.task_dependency_create", "task_dependencies", d.id);
  return ok({ id: d.id, version: 1, source: "MANUAL", data_classification: "internal", created_at: stamp, updated_at: stamp, task_id: t.id, depends_on_task_id: other.id, dependency_type: "finish_to_start" }, 201);
}
function removeDep(req: MockRequest): Response {
  const t = getTask(req.claims, req.params.id ?? "", "write");
  const d = liveDeps().find((x) => x.id === req.params.dependency_id && x.task_id === t.id);
  if (!d) throw err(404, "NOT_FOUND", "dependency not found");
  d.deleted = true;
  recordAudit(req.claims, "execution.task_dependency_delete", "task_dependencies", d.id);
  return ok(null, 204);
}

// ---------------------------------------------------------------- EP-TASK-19 reassign request
function reassignRequest(req: MockRequest): Response {
  requireIdem(req);
  const c = req.claims;
  const t = getTask(c, req.params.id ?? "", "write");
  const b = body(req);
  const to = typeof b.to_assignee_id === "string" ? b.to_assignee_id.trim() : "";
  const reason = typeof b.reason === "string" ? b.reason.trim() : "";
  if (!to) throw err(422, "VALIDATION_ERROR", "to_assignee_id is required", { field: "to_assignee_id" });
  if (!reason || reason.length > 500) throw err(422, "VALIDATION_ERROR", "reason must be 1..500 chars", { field: "reason" });
  if (level(c, "write") !== "o") throw biz("direct reassign allowed", { reason: "direct_reassign_allowed" });
  if (t.status === "done" || t.status === "cancelled") throw err(409, "CONFLICT_STATE", "task is closed", { status: t.status });
  return ok(createReassignRequest(c, t, to, reason), 201);
}

export const WORK_ROUTES: readonly Route[] = [
  { method: "GET", pattern: "/work/tasks", permission: "execution:read", handler: listTasks },
  { method: "POST", pattern: "/work/tasks", permission: "execution:write", handler: createTask },
  { method: "GET", pattern: "/work/tasks/:id", permission: "execution:read", handler: (req) => ok(taskOut(getTask(req.claims, req.params.id ?? ""))) },
  { method: "PATCH", pattern: "/work/tasks/:id", permission: "execution:write", handler: patchTask },
  { method: "DELETE", pattern: "/work/tasks/:id", permission: "execution:write", handler: deleteTask },
  { method: "GET", pattern: "/work/tasks/:id/dependencies", permission: "execution:read", handler: listDeps },
  { method: "POST", pattern: "/work/tasks/:id/dependencies", permission: "execution:write", handler: addDep },
  { method: "DELETE", pattern: "/work/tasks/:id/dependencies/:dependency_id", permission: "execution:write", handler: removeDep },
  { method: "POST", pattern: "/work/tasks/:id/reassign-requests", permission: "execution:write", handler: reassignRequest },
];

/**
 * Mock `/work/projects*`, milestones and `/work/workload` (T-625F, EP-TASK-09..18). Progress =
 * done / non-cancelled tasks; planned = linear start→due at today; `late` = planned − progress
 * > 10 pts (METRIC-OPS-02, 03 §4). EMP sees projects they own or have a task in. Workload = Σ
 * estimate (missing → 4 h) of open tasks per ISO week ÷ 40 h (DEC-226); `overloaded` = > 110 %
 * in the last two weeks. No names (R-DEC-44).
 */
import type { MockClaims } from "./fixtures";
import { MockHttpError, ok, paginate, parsePage } from "./http";
import { recordAudit } from "./audit";
import type { MockRequest, Route } from "./router";
import { newWorkId, selfIds, workStore, workToday, type MMilestone, type MProject } from "./work-store";
import { allowed, biz, err, expectVersion, isDate, isOverdue, level, requireIdem, STATUSES, taskVisible } from "./work";
import { isIsoWeek, isoWeek, weekRange, weeksEnding } from "@/lib/work-dates";

const LATE_GAP_PCT = 10; // 03 §4 METRIC-OPS-02
const DEFAULT_TASK_HOURS = 4;
const CAPACITY_HOURS = 40;
const THRESHOLD_PCT = 110;
const OVERLOAD_WEEKS = 2;
const PROJECT_STATUSES = ["planned", "active", "on_hold", "done", "cancelled"];
const body = (req: MockRequest) => (req.body && typeof req.body === "object" ? (req.body as Record<string, unknown>) : {});
const round1 = (n: number) => Math.round(n * 10) / 10;
const daysBetween = (a: string, b: string) => (Date.parse(`${b}T00:00:00Z`) - Date.parse(`${a}T00:00:00Z`)) / 86_400_000;

const projTasks = (p: MProject) => workStore().tasks.filter((t) => !t.deleted && t.project_id === p.id);

function projectVisible(c: MockClaims, p: MProject, action: "read" | "write" = "read"): boolean {
  if (allowed(c, action, p.department_id, [p.owner_id])) return true;
  if (action === "read" && level(c) === "o") {
    const me = selfIds(c);
    return projTasks(p).some((t) => t.assignee_id !== null && me.has(t.assignee_id));
  }
  return false;
}

export function projectOut(p: MProject, today = workToday()) {
  const { deleted: _d, ...rest } = p;
  void _d;
  const tasks = projTasks(p);
  const counted = tasks.filter((t) => t.status !== "cancelled");
  const progress = counted.length ? round1((counted.filter((t) => t.status === "done").length / counted.length) * 100) : null;
  let planned: number | null = null;
  if (p.start_date && p.due_date) {
    const span = daysBetween(p.start_date, p.due_date);
    planned = span <= 0 ? 100 : round1(Math.min(100, Math.max(0, (daysBetween(p.start_date, today) / span) * 100)));
  }
  const late = progress !== null && planned !== null && p.status !== "done" && p.status !== "cancelled" ? planned - progress > LATE_GAP_PCT : false;
  return {
    ...rest, progress_pct: progress, planned_pct: planned, late,
    open_tasks: tasks.filter((t) => t.status !== "done" && t.status !== "cancelled").length,
    overdue_tasks: tasks.filter((t) => isOverdue(t, today)).length,
  };
}
export const milestoneOut = (m: MMilestone, today = workToday()) => {
  const { deleted: _d, ...rest } = m;
  void _d;
  return { ...rest, initiative_id: null, source: "MANUAL", data_classification: "internal", late: m.status === "planned" && m.due_date < today };
};

function getProject(c: MockClaims, id: string, action: "read" | "write" = "read"): MProject {
  const p = workStore().projects.find((x) => x.id === id && !x.deleted);
  if (!p || !projectVisible(c, p)) throw err(404, "NOT_FOUND", "project not found");
  if (action === "write" && !projectVisible(c, p, "write")) throw err(403, "FORBIDDEN_SCOPE", "project outside your scope", { department_id: String(p.department_id) });
  return p;
}

function listProjects(req: MockRequest): Response {
  const q = req.query;
  const page = parsePage(q, ["start_date", "planned_end_date", "name"]);
  const status = q.get("status");
  if (status && !PROJECT_STATUSES.includes(status)) throw err(422, "VALIDATION_ERROR", "invalid status", { field: "status" });
  const today = workToday();
  const rows = workStore().projects.filter((p) => !p.deleted && projectVisible(req.claims, p)
    && (!status || p.status === status) && (!q.get("department_id") || p.department_id === q.get("department_id"))
    && (!q.get("owner_id") || p.owner_id === q.get("owner_id")) && (!q.get("initiative_id") || p.initiative_id === q.get("initiative_id")))
    .map((p) => projectOut(p, today))
    .filter((p) => q.get("late") !== "true" || p.late);
  // `planned_end_date` is the ORM column behind `due_date` (v2.1 sort whitelist)
  return paginate(rows as unknown as Record<string, unknown>[], page.sortBy === "planned_end_date" ? { ...page, sortBy: "due_date" } : page);
}

function projectDetail(req: MockRequest): Response {
  const p = getProject(req.claims, req.params.id ?? "");
  const today = workToday();
  const by_status = Object.fromEntries(STATUSES.map((s) => [s, 0])) as Record<string, number>;
  for (const t of projTasks(p)) if (taskVisible(req.claims, t) || level(req.claims) === "o") by_status[t.status] = (by_status[t.status] ?? 0) + 1;
  const milestones = workStore().milestones.filter((m) => !m.deleted && m.project_id === p.id).sort((a, b) => a.due_date.localeCompare(b.due_date)).map((m) => milestoneOut(m, today));
  return ok({ ...projectOut(p, today), milestones, task_counts: { by_status } });
}

function createProject(req: MockRequest): Response {
  requireIdem(req);
  const c = req.claims;
  const b = body(req);
  for (const f of ["code", "name", "owner_id"]) if (typeof b[f] !== "string" || !(b[f] as string).trim()) throw err(422, "VALIDATION_ERROR", `${f} is required`, { field: f });
  for (const f of ["start_date", "due_date"]) if (b[f] && !isDate(b[f])) throw err(422, "VALIDATION_ERROR", `${f} must be a date`, { field: f });
  if (b.status && !PROJECT_STATUSES.includes(String(b.status))) throw err(422, "VALIDATION_ERROR", "invalid status", { field: "status" });
  if (b.start_date && b.due_date && String(b.due_date) < String(b.start_date)) throw biz("due_date must be on/after start_date", { field: "due_date" });
  if (b.initiative_id) throw biz("initiative not found", { field: "initiative_id" });
  const code = String(b.code).trim();
  if (workStore().projects.some((p) => !p.deleted && p.code === code)) throw err(409, "DUPLICATE_RESOURCE", "project code exists", { field: "code" });
  const lvl = level(c, "write");
  if (lvl === "o" && !selfIds(c).has(String(b.owner_id))) throw err(403, "FORBIDDEN_SCOPE", "owner outside your scope", { field: "owner_id" });
  const dept = lvl === "all" ? ((b.department_id as string | null) ?? null) : c.department_id;
  if (lvl !== "all" && b.department_id && b.department_id !== c.department_id) throw err(403, "FORBIDDEN_SCOPE", "department outside your scope", { department_id: String(b.department_id) });
  const stamp = new Date().toISOString();
  const p: MProject = { id: newWorkId("project"), version: 1, source: "MANUAL", data_classification: "internal", created_at: stamp, updated_at: stamp, code, name: String(b.name).trim(),
    owner_id: String(b.owner_id), department_id: dept, start_date: (b.start_date as string) || null, due_date: (b.due_date as string) || null, actual_end_date: null,
    status: (b.status as string) ?? "planned", budget_amount: (b.budget_amount as number | null) ?? null, currency: "VND", initiative_id: null, deleted: false };
  workStore().projects.push(p);
  recordAudit(c, "execution.project_create", "projects", p.id);
  return ok(projectOut(p), 201);
}

function patchProject(req: MockRequest): Response {
  const p = getProject(req.claims, req.params.id ?? "", "write");
  expectVersion(req, p.version);
  const b = body(req);
  if (b.status && !PROJECT_STATUSES.includes(String(b.status))) throw err(422, "VALIDATION_ERROR", "invalid status", { field: "status" });
  for (const f of ["name", "start_date", "due_date", "status", "actual_end_date", "budget_amount"] as const) if (f in b) (p as unknown as Record<string, unknown>)[f] = b[f];
  Object.assign(p, { version: p.version + 1, updated_at: new Date().toISOString() });
  recordAudit(req.claims, "execution.project_update", "projects", p.id);
  return ok(projectOut(p));
}

function deleteProject(req: MockRequest): Response {
  const p = getProject(req.claims, req.params.id ?? "", "write");
  p.deleted = true;
  recordAudit(req.claims, "execution.project_delete", "projects", p.id);
  return ok(null, 204);
}

// ---------------------------------------------------------------- milestones EP-TASK-14..17
const MS_STATUSES = ["planned", "done", "missed"];
function listMilestones(req: MockRequest): Response {
  const p = getProject(req.claims, req.params.id ?? "");
  const rows = workStore().milestones.filter((m) => !m.deleted && m.project_id === p.id).sort((a, b) => a.due_date.localeCompare(b.due_date)).map((m) => milestoneOut(m));
  return ok(rows);
}
function getMilestone(req: MockRequest): MMilestone {
  const p = getProject(req.claims, req.params.id ?? "", "write");
  const m = workStore().milestones.find((x) => !x.deleted && x.id === req.params.milestone_id && x.project_id === p.id);
  if (!m) throw err(404, "NOT_FOUND", "milestone not found");
  return m;
}
function createMilestone(req: MockRequest): Response {
  requireIdem(req);
  const p = getProject(req.claims, req.params.id ?? "", "write");
  const b = body(req);
  if (typeof b.title !== "string" || !b.title.trim()) throw err(422, "VALIDATION_ERROR", "title is required", { field: "title" });
  if (!isDate(b.due_date)) throw err(422, "VALIDATION_ERROR", "due_date must be a date", { field: "due_date" });
  if (b.status && !MS_STATUSES.includes(String(b.status))) throw err(422, "VALIDATION_ERROR", "invalid status", { field: "status" });
  const stamp = new Date().toISOString();
  const status = (b.status as MMilestone["status"]) ?? "planned";
  const m: MMilestone = { id: newWorkId("milestone"), version: 1, project_id: p.id, title: b.title.trim(), due_date: b.due_date, status, done_at: status === "done" ? stamp : null, created_at: stamp, updated_at: stamp, deleted: false };
  workStore().milestones.push(m);
  recordAudit(req.claims, "execution.milestone_create", "milestones", m.id);
  return ok(milestoneOut(m), 201);
}
function patchMilestone(req: MockRequest): Response {
  const m = getMilestone(req);
  expectVersion(req, m.version);
  const b = body(req);
  if (b.status && !MS_STATUSES.includes(String(b.status))) throw err(422, "VALIDATION_ERROR", "invalid status", { field: "status" });
  if ("due_date" in b && !isDate(b.due_date)) throw err(422, "VALIDATION_ERROR", "due_date must be a date", { field: "due_date" });
  if (typeof b.title === "string" && b.title.trim()) m.title = b.title.trim();
  if (isDate(b.due_date)) m.due_date = b.due_date;
  if (b.status) {
    m.done_at = b.status === "done" ? (m.status === "done" ? m.done_at : new Date().toISOString()) : null;
    m.status = b.status as MMilestone["status"];
  }
  Object.assign(m, { version: m.version + 1, updated_at: new Date().toISOString() });
  recordAudit(req.claims, "execution.milestone_update", "milestones", m.id);
  return ok(milestoneOut(m));
}
function deleteMilestone(req: MockRequest): Response {
  const m = getMilestone(req);
  m.deleted = true;
  for (const t of workStore().tasks) if (t.milestone_id === m.id) t.milestone_id = null;
  recordAudit(req.claims, "execution.milestone_delete", "milestones", m.id);
  return ok(null, 204);
}

// ---------------------------------------------------------------- EP-TASK-18 workload
function workload(req: MockRequest): Response {
  const c = req.claims;
  const q = req.query;
  const week = q.get("week") || isoWeek(workToday());
  if (!isIsoWeek(week)) throw new MockHttpError(400, "BAD_REQUEST", "week must be YYYY-Www", { param: "week" });
  const rawWeeks = q.get("weeks");
  const n = rawWeeks === null || rawWeeks === "" ? 4 : Number(rawWeeks);
  if (!Number.isInteger(n) || n < 1 || n > 8) throw err(422, "VALIDATION_ERROR", "weeks must be 1..8", { field: "weeks" });
  let dept = q.get("department_id");
  if (level(c, "query") === "d") {
    if (dept && dept !== c.department_id) throw err(403, "FORBIDDEN_SCOPE", "department outside your scope", { department_id: dept });
    dept = c.department_id;
  }
  const weeks = weeksEnding(week, Math.max(n, OVERLOAD_WEEKS));
  const shown = weeks.slice(-n);
  const tasks = workStore().tasks.filter((t) => !t.deleted && t.assignee_id && t.status !== "cancelled" && (!dept || t.department_id === dept));
  const people = new Map<string, { dept: string | null; cells: Map<string, { hours: number; open: number }> }>();
  for (const w of weeks) {
    const { start, end } = weekRange(w);
    const s = `${start}T00:00:00Z`;
    const e = `${end}T23:59:59.999Z`;
    for (const t of tasks) {
      if (!(t.created_at <= e && (t.done_at === null || t.done_at >= s))) continue;
      const row = people.get(t.assignee_id as string) ?? { dept: t.department_id, cells: new Map() };
      const cell = row.cells.get(w) ?? { hours: 0, open: 0 };
      cell.hours += t.estimate_hours ?? DEFAULT_TASK_HOURS;
      cell.open += 1;
      row.cells.set(w, cell);
      people.set(t.assignee_id as string, row);
    }
  }
  const pct = (h: number) => Math.round((h / CAPACITY_HOURS) * 10_000) / 100;
  const last = weeks.slice(-OVERLOAD_WEEKS);
  const rows = [...people.entries()].filter(([, r]) => shown.some((w) => r.cells.has(w))).map(([employee_id, r]) => ({
    employee_id, department_id: r.dept,
    cells: shown.map((w) => ({ week: w, load_pct: pct(r.cells.get(w)?.hours ?? 0), hours: r.cells.get(w)?.hours ?? 0, open_tasks: r.cells.get(w)?.open ?? 0 })),
    overloaded: last.every((w) => pct(r.cells.get(w)?.hours ?? 0) > THRESHOLD_PCT),
  })).sort((a, b) => Number(b.overloaded) - Number(a.overloaded) || (b.cells.at(-1)?.load_pct ?? 0) - (a.cells.at(-1)?.load_pct ?? 0) || a.employee_id.localeCompare(b.employee_id));
  const over = rows.filter((r) => r.overloaded).length;
  return ok({ weeks: shown, threshold_pct: THRESHOLD_PCT, overload_weeks: OVERLOAD_WEEKS, capacity_hours: CAPACITY_HOURS, rows,
    summary: { people: rows.length, overloaded_count: over, overloaded_pct: rows.length ? Math.round((over / rows.length) * 1000) / 10 : 0 } });
}

export const PROJECT_ROUTES: readonly Route[] = [
  { method: "GET", pattern: "/work/workload", permission: "execution:query", handler: workload },
  { method: "GET", pattern: "/work/projects", permission: "execution:read", handler: listProjects },
  { method: "POST", pattern: "/work/projects", permission: "execution:write", handler: createProject },
  { method: "GET", pattern: "/work/projects/:id", permission: "execution:read", handler: projectDetail },
  { method: "PATCH", pattern: "/work/projects/:id", permission: "execution:write", handler: patchProject },
  { method: "DELETE", pattern: "/work/projects/:id", permission: "execution:write", handler: deleteProject },
  { method: "GET", pattern: "/work/projects/:id/milestones", permission: "execution:read", handler: listMilestones },
  { method: "POST", pattern: "/work/projects/:id/milestones", permission: "execution:write", handler: createMilestone },
  { method: "PATCH", pattern: "/work/projects/:id/milestones/:milestone_id", permission: "execution:write", handler: patchMilestone },
  { method: "DELETE", pattern: "/work/projects/:id/milestones/:milestone_id", permission: "execution:write", handler: deleteMilestone },
];

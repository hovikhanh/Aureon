/** Mock EP-STR-01..22 (10 §7.2.3): tree, Strategy / StrategicObjective CRUD, Initiatives (+ projects). */
import { recordAudit } from "./audit";
import { ok, paginate, parsePage } from "./http";
import type { MockRequest, Route } from "./router";
import { canRead, canWrite, forbiddenScope, pinDepartment, requireManager, requireSoWrite, requireStrategyWrite } from "./goal-scope";
import { periodBounds, onTrack } from "./goals-rules";
import { base, goalStore, newGoalId, recomputeSo, type MInitiative, type MSO, type MStrategy, type Pillar } from "./goals-store";
import { buildTree, currentQuarter } from "./goals-tree";
import { biz, body, err, expectVersion, invalid, isDate, notFound, nowIso, num, oneOf, PILLARS, requireIdem, str, strip } from "./goals-http";
import { workStore, workToday } from "./work-store";

const STATUSES = ["draft", "active", "closed"] as const;
const INI_STATUSES = ["planned", "active", "at_risk", "done", "cancelled"] as const;

function tree(req: MockRequest) {
  const q = req.query;
  const period = q.get("period_key") || currentQuarter();
  if (!periodBounds(period)) throw err(400, "BAD_REQUEST", "invalid period_key", { param: "period_key" });
  return ok(buildTree(req.claims, { periodKey: period, departmentId: q.get("department_id") || null, strategyId: q.get("strategy_id") || null }));
}

// ---------------------------------------------------------------- Strategy (EP-STR-02..06)
const liveStrategies = () => goalStore().strategies.filter((x) => !x.deleted);
function getStrategy(id: string): MStrategy {
  const st = liveStrategies().find((x) => x.id === id);
  if (!st) throw notFound("strategy");
  return st;
}
function checkOverlap(st: Pick<MStrategy, "id" | "status" | "period_start" | "period_end">): void {
  if (st.status !== "active") return;
  const clash = liveStrategies().some((x) => x.id !== st.id && x.status === "active" && x.period_start < st.period_end && st.period_start < x.period_end);
  if (clash) throw biz("overlapping active strategy", { reason: "overlapping_active_strategy" });
}
function createStrategy(req: MockRequest) {
  requireIdem(req);
  requireStrategyWrite(req.claims);
  const b = body(req);
  const code = str(b, "code", true, 50)!;
  const start = b.period_start;
  const end = b.period_end;
  if (!isDate(start)) throw invalid("period_start");
  if (!isDate(end)) throw invalid("period_end");
  if (end <= start) throw invalid("period_end", "period_end must be after period_start");
  if (liveStrategies().some((x) => x.code === code)) throw err(409, "DUPLICATE_RESOURCE", "strategy code exists", { field: "code" });
  const at = nowIso();
  const st: MStrategy = { ...base(newGoalId("strategy"), at), source: "MANUAL", code, name: str(b, "name", true)!, vision: str(b, "vision", false, 5000), mission: str(b, "mission", false, 5000),
    period_start: start, period_end: end, owner_id: str(b, "owner_id", true)!, status: oneOf(b, "status", STATUSES, "draft")! };
  checkOverlap(st);
  goalStore().strategies.push(st);
  recordAudit(req.claims, "execution.strategy_create", "strategies", st.id);
  return ok(strip(st), 201);
}
function patchStrategy(req: MockRequest) {
  requireStrategyWrite(req.claims);
  const st = getStrategy(req.params.id!);
  expectVersion(req, st.version);
  const b = body(req);
  const next = { ...st };
  for (const f of ["name", "vision", "mission", "owner_id"] as const) if (f in b) (next as Record<string, unknown>)[f] = str(b, f, f === "name" || f === "owner_id", f === "name" || f === "owner_id" ? 500 : 5000);
  for (const f of ["period_start", "period_end"] as const) if (f in b) { if (!isDate(b[f])) throw invalid(f); next[f] = b[f] as string; }
  if ("status" in b) next.status = oneOf(b, "status", STATUSES)!;
  if (next.period_end <= next.period_start) throw invalid("period_end", "period_end must be after period_start");
  checkOverlap(next);
  Object.assign(st, next, { version: st.version + 1, updated_at: nowIso() });
  recordAudit(req.claims, "execution.strategy_update", "strategies", st.id);
  return ok(strip(st));
}
function deleteStrategy(req: MockRequest) {
  requireStrategyWrite(req.claims);
  const st = getStrategy(req.params.id!);
  if (goalStore().sos.some((x) => !x.deleted && x.strategy_id === st.id)) throw biz("strategy has live strategic objectives", { reason: "has_live_children" });
  st.deleted = true;
  recordAudit(req.claims, "execution.strategy_delete", "strategies", st.id);
  return ok(null, 204);
}

// ---------------------------------------------------------------- StrategicObjective (EP-STR-07..11)
const liveSos = () => goalStore().sos.filter((x) => !x.deleted);
function soOut(so: MSO) {
  const s = goalStore();
  const n = <T extends { deleted: boolean; strategic_objective_id: string | null }>(rows: T[]) => rows.filter((r) => !r.deleted && r.strategic_objective_id === so.id).length;
  return { ...strip(so), kpi_count: n(s.kpis), objective_count: n(s.objectives), initiative_count: n(s.initiatives) };
}
function getSo(req: MockRequest): MSO {
  const so = liveSos().find((x) => x.id === req.params.id);
  if (!so) throw notFound("strategic objective");
  if (!canRead(req.claims, so)) throw forbiddenScope("strategic objective");
  return so;
}
function listSos(req: MockRequest) {
  const q = req.query;
  const rows = liveSos().filter((so) => canRead(req.claims, so) && (!q.get("strategy_id") || so.strategy_id === q.get("strategy_id"))
    && (!q.get("pillar") || so.pillar === q.get("pillar")) && (!q.get("department_id") || so.department_id === q.get("department_id")));
  return paginate(rows.map(soOut) as unknown as Record<string, unknown>[], parsePage(q, ["sort_order", "code"]));
}
function createSo(req: MockRequest) {
  requireIdem(req);
  const b = body(req);
  const pillar = oneOf(b, "pillar", PILLARS);
  requireSoWrite(req.claims, pillar);
  const strategyId = str(b, "strategy_id", true)!;
  if (!liveStrategies().some((x) => x.id === strategyId)) throw biz("strategy not found", { field: "strategy_id" });
  const code = str(b, "code", true, 50)!;
  if (liveSos().some((x) => x.code === code)) throw err(409, "DUPLICATE_RESOURCE", "strategic objective code exists", { field: "code" });
  const at = nowIso();
  const so: MSO = { ...base(newGoalId("strategic_objective"), at), source: "MANUAL", strategy_id: strategyId, code, title: str(b, "title", true)!, description: str(b, "description", false, 5000),
    pillar: pillar as Pillar | null, owner_id: str(b, "owner_id", true)!, department_id: str(b, "department_id", false), weight_pct: num(b, "weight_pct", false) ?? 0,
    sort_order: num(b, "sort_order", false) ?? liveSos().length + 1, status: "active", progress_pct: 0 };
  goalStore().sos.push(so);
  recordAudit(req.claims, "execution.strategic_objective_create", "strategic_objectives", so.id);
  return ok(soOut(so), 201);
}
function patchSo(req: MockRequest) {
  const so = getSo(req);
  const b = body(req);
  requireSoWrite(req.claims, so.pillar);
  if ("pillar" in b) requireSoWrite(req.claims, oneOf(b, "pillar", PILLARS));
  expectVersion(req, so.version);
  for (const f of ["code", "title", "description", "owner_id", "department_id"] as const) if (f in b) (so as unknown as Record<string, unknown>)[f] = str(b, f, f === "code" || f === "title" || f === "owner_id", f === "description" ? 5000 : 500);
  if ("pillar" in b) so.pillar = oneOf(b, "pillar", PILLARS) as Pillar | null;
  if ("weight_pct" in b) so.weight_pct = num(b, "weight_pct", true)!;
  if ("sort_order" in b) so.sort_order = num(b, "sort_order", true)!;
  if ("status" in b) so.status = oneOf(b, "status", STATUSES)!;
  Object.assign(so, { version: so.version + 1, updated_at: nowIso() });
  recordAudit(req.claims, "execution.strategic_objective_update", "strategic_objectives", so.id);
  return ok(soOut(so));
}
function deleteSo(req: MockRequest) {
  const so = getSo(req);
  requireSoWrite(req.claims, so.pillar);
  const o = soOut(so);
  if (o.kpi_count + o.objective_count + o.initiative_count > 0) throw biz("strategic objective has live links", { reason: "has_live_links" });
  so.deleted = true;
  recordAudit(req.claims, "execution.strategic_objective_delete", "strategic_objectives", so.id);
  return ok(null, 204);
}

// ---------------------------------------------------------------- Initiative (EP-STR-12..16, 22)
const liveInis = () => goalStore().initiatives.filter((x) => !x.deleted);
const iniProjects = (i: MInitiative) => workStore().projects.filter((p) => !p.deleted && (i.project_codes.includes(p.code) || p.initiative_id === i.id));
function iniOut(i: MInitiative) {
  const { project_codes: _p, ...rest } = strip(i);
  void _p;
  return { ...rest, on_track: onTrack(i.progress_pct, i.start_date, i.planned_end_date, workToday()) };
}
function getIni(req: MockRequest, action: "read" | "write" = "read"): MInitiative {
  const i = liveInis().find((x) => x.id === req.params.id);
  if (!i) throw notFound("initiative");
  if (!canRead(req.claims, i)) throw forbiddenScope("initiative");
  if (action === "write") {
    requireManager(req.claims, "write initiatives");
    if (!canWrite(req.claims, i)) throw forbiddenScope("initiative");
  }
  return i;
}
function listInis(req: MockRequest) {
  const q = req.query;
  const eq = (f: "objective_id" | "status" | "pillar" | "strategic_objective_id", i: MInitiative) => !q.get(f) || i[f] === q.get(f);
  const rows = liveInis().filter((i) => canRead(req.claims, i) && eq("objective_id", i) && eq("status", i) && eq("pillar", i) && eq("strategic_objective_id", i));
  return paginate(rows.map(iniOut) as unknown as Record<string, unknown>[], parsePage(q, ["code", "planned_end_date", "progress_pct", "start_date"]));
}
function createIni(req: MockRequest) {
  requireIdem(req);
  requireManager(req.claims, "create initiatives");
  const b = body(req);
  const s = goalStore();
  const soId = str(b, "strategic_objective_id", false);
  const so = soId ? liveSos().find((x) => x.id === soId) : undefined;
  if (!so || !canRead(req.claims, so)) throw biz("strategic objective not found", { field: "strategic_objective_id" });
  const objectiveId = str(b, "objective_id", false);
  if (objectiveId && !s.objectives.some((o) => !o.deleted && o.id === objectiveId && canRead(req.claims, o))) throw biz("objective not found", { field: "objective_id" });
  const code = str(b, "code", true, 50)!;
  if (liveInis().some((x) => x.code === code)) throw err(409, "DUPLICATE_RESOURCE", "initiative code exists", { field: "code" });
  const start = b.start_date;
  const end = b.planned_end_date;
  if (!isDate(start)) throw invalid("start_date");
  if (!isDate(end) || end < start) throw invalid("planned_end_date");
  const pillar = (oneOf(b, "pillar", PILLARS) ?? so.pillar) as Pillar | null;
  const dept = pinDepartment(req.claims, str(b, "department_id", false), pillar);
  const at = nowIso();
  const i: MInitiative = { ...base(newGoalId("initiative"), at), source: "MANUAL", code, title: str(b, "title", true)!, description: str(b, "description", false, 5000),
    objective_id: objectiveId, strategic_objective_id: so.id, pillar, owner_id: str(b, "owner_id", true)!, department_id: dept, start_date: start, planned_end_date: end,
    status: oneOf(b, "status", INI_STATUSES, "planned")!, progress_pct: 0, weight_pct: num(b, "weight_pct", false) ?? 0, budget_amount: num(b, "budget_amount", false),
    currency: "VND", project_codes: [] };
  s.initiatives.push(i);
  recomputeSo(s, so);
  recordAudit(req.claims, "execution.initiative_create", "initiatives", i.id);
  return ok(iniOut(i), 201);
}
function patchIni(req: MockRequest) {
  const i = getIni(req, "write");
  expectVersion(req, i.version);
  const b = body(req);
  if ("progress_pct" in b) throw invalid("progress_pct", "progress_pct is computed");
  for (const f of ["title", "description", "owner_id"] as const) if (f in b) (i as unknown as Record<string, unknown>)[f] = str(b, f, f !== "description", f === "description" ? 5000 : 500);
  if ("status" in b) i.status = oneOf(b, "status", INI_STATUSES)!;
  if ("weight_pct" in b) i.weight_pct = num(b, "weight_pct", true)!;
  Object.assign(i, { version: i.version + 1, updated_at: nowIso() });
  const so = liveSos().find((x) => x.id === i.strategic_objective_id);
  if (so) recomputeSo(goalStore(), so);
  recordAudit(req.claims, "execution.initiative_update", "initiatives", i.id);
  return ok(iniOut(i));
}
function deleteIni(req: MockRequest) {
  const i = getIni(req, "write");
  if (iniProjects(i).length || workStore().tasks.some((t) => !t.deleted && t.initiative_id === i.id)) {
    throw err(409, "CONFLICT_STATE", "initiative still has milestones, tasks, decisions, KPIs or projects", { initiative_id: i.id });
  }
  i.deleted = true;
  const so = liveSos().find((x) => x.id === i.strategic_objective_id);
  if (so) recomputeSo(goalStore(), so);
  recordAudit(req.claims, "execution.initiative_delete", "initiatives", i.id);
  return ok(null, 204);
}
function iniProjectsOut(req: MockRequest) {
  const i = getIni(req);
  const projects = iniProjects(i).filter((p) => canRead(req.claims, { department_id: p.department_id, pillar: null, owner_id: p.owner_id }) || req.claims.role !== "EMP");
  return ok(projects.map((p) => ({ id: p.id, code: p.code, name: p.name, status: p.status, start_date: p.start_date, planned_end_date: p.due_date, owner_id: p.owner_id })));
}

const R = "execution:read";
const W = "execution:write";
export const STRATEGY_ROUTES: readonly Route[] = [
  { method: "GET", pattern: "/goals/tree", permission: R, handler: tree },
  { method: "GET", pattern: "/goals/strategies", permission: R, handler: (req) => paginate(liveStrategies().filter((x) => !req.query.get("status") || x.status === req.query.get("status")).map(strip) as unknown as Record<string, unknown>[], parsePage(req.query, ["code", "period_start"])) },
  { method: "POST", pattern: "/goals/strategies", permission: W, handler: createStrategy },
  { method: "GET", pattern: "/goals/strategies/:id", permission: R, handler: (req) => ok(strip(getStrategy(req.params.id!))) },
  { method: "PATCH", pattern: "/goals/strategies/:id", permission: W, handler: patchStrategy },
  { method: "DELETE", pattern: "/goals/strategies/:id", permission: W, handler: deleteStrategy },
  { method: "GET", pattern: "/goals/strategic-objectives", permission: R, handler: listSos },
  { method: "POST", pattern: "/goals/strategic-objectives", permission: W, handler: createSo },
  { method: "GET", pattern: "/goals/strategic-objectives/:id", permission: R, handler: (req) => ok(soOut(getSo(req))) },
  { method: "PATCH", pattern: "/goals/strategic-objectives/:id", permission: W, handler: patchSo },
  { method: "DELETE", pattern: "/goals/strategic-objectives/:id", permission: W, handler: deleteSo },
  { method: "GET", pattern: "/goals/initiatives", permission: R, handler: listInis },
  { method: "POST", pattern: "/goals/initiatives", permission: W, handler: createIni },
  { method: "GET", pattern: "/goals/initiatives/:id", permission: R, handler: (req) => ok(iniOut(getIni(req))) },
  { method: "PATCH", pattern: "/goals/initiatives/:id", permission: W, handler: patchIni },
  { method: "DELETE", pattern: "/goals/initiatives/:id", permission: W, handler: deleteIni },
  // EP-STR-17 initiative milestones: mock-only empty list (no SCR in M1.4 edits them)
  { method: "GET", pattern: "/goals/initiatives/:id/milestones", permission: R, handler: (req) => { getIni(req); return paginate([], parsePage(req.query)); } },
  { method: "GET", pattern: "/goals/initiatives/:id/projects", permission: R, handler: iniProjectsOut },
];

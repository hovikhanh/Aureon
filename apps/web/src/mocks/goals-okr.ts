/** Mock EP-OKR-01..11 + EP-PRF-01/02/05/06 (10 §7.2.3, R-DEC-55/57). */
import { recordAudit } from "./audit";
import { ok, paginate, parsePage } from "./http";
import type { MockRequest, Route } from "./router";
import { canCheckIn, canRead, canWrite, forbiddenScope, pinDepartment, requireManager, type Scoped } from "./goal-scope";
import { daysBetween, krProgressPct, periodBounds, periodKeyFor, KR_CHECKIN_MAX_AGE_DAYS } from "./goals-rules";
import { base, checkInKr, goalStore, newGoalId, recomputeObjective, type MCheckIn, type MKr, type MObjective, type Pillar } from "./goals-store";
import { notifyGoalAlert } from "./goals-notify";
import { parseCheckIn } from "./goals-kpi";
import { biz, body, err, expectVersion, invalid, notFound, nowIso, num, oneOf, PILLARS, requireIdem, str, strip } from "./goals-http";
import { workToday } from "./work-store";

const LEVELS = ["company", "department", "team", "individual"] as const;
const STATUSES = ["draft", "active", "closed"] as const;
const MIN_KR = 2;
const MAX_KR = 5;

const liveObjs = () => goalStore().objectives.filter((o) => !o.deleted);
const liveKrs = () => goalStore().krs.filter((k) => !k.deleted);
const krsOf = (oid: string) => liveKrs().filter((k) => k.objective_id === oid);
const objOut = (o: MObjective) => ({ ...strip(o), at_risk_kr_count: krsOf(o.id).filter((k) => k.at_risk).length });
const krOut = (k: MKr) => strip(k);
/** A KR is scoped by its Objective's department/pillar + its own owner. */
export const krScope = (k: MKr): Scoped => {
  const o = goalStore().objectives.find((x) => x.id === k.objective_id);
  return { department_id: o?.department_id ?? null, pillar: o?.pillar ?? null, owner_id: k.owner_id };
};
const objVisible = (c: MockRequest["claims"], o: MObjective) => canRead(c, o) || krsOf(o.id).some((k) => canRead(c, krScope(k)));

function getObj(req: MockRequest, action: "read" | "write" = "read"): MObjective {
  const o = liveObjs().find((x) => x.id === req.params.id);
  if (!o) throw notFound("objective");
  if (!objVisible(req.claims, o)) throw forbiddenScope("objective");
  if (action === "write") {
    requireManager(req.claims, "write objectives");
    if (!canWrite(req.claims, o)) throw forbiddenScope("objective");
  }
  return o;
}
export function getKr(req: MockRequest, action: "read" | "write" = "read"): MKr {
  const k = liveKrs().find((x) => x.id === req.params.id);
  if (!k) throw notFound("key result");
  const sc = krScope(k);
  if (!canRead(req.claims, sc)) throw forbiddenScope("key result");
  if (action === "write") {
    requireManager(req.claims, "write key results");
    if (!canWrite(req.claims, sc)) throw forbiddenScope("key result");
  }
  return k;
}

function listObjs(req: MockRequest) {
  const q = req.query;
  const eq = (f: "period_key" | "owner_id" | "strategic_objective_id" | "department_id" | "parent_id", o: MObjective) => !q.get(f) || o[f] === q.get(f);
  const risk = q.get("at_risk");
  const rows = liveObjs().filter((o) => objVisible(req.claims, o) && eq("period_key", o) && eq("owner_id", o) && eq("strategic_objective_id", o) && eq("department_id", o)
    && eq("parent_id", o) && (risk === null || risk === "" || (risk === "true") === krsOf(o.id).some((k) => k.at_risk)));
  return paginate(rows.map(objOut) as unknown as Record<string, unknown>[], parsePage(q, ["period_key", "title", "updated_at"]));
}

function createObj(req: MockRequest) {
  requireIdem(req);
  requireManager(req.claims, "create objectives");
  const b = body(req);
  const parent = str(b, "parent_id", false);
  const so = str(b, "strategic_objective_id", false);
  if (parent && so) throw biz("only root objectives link a strategic objective", { field: "strategic_objective_id" });
  if (so && !goalStore().sos.some((x) => !x.deleted && x.id === so)) throw biz("strategic objective not found", { field: "strategic_objective_id" });
  const period = str(b, "period_key", true, 10)!;
  if (!periodBounds(period)) throw invalid("period_key");
  const status = oneOf(b, "status", STATUSES, "draft")!;
  if (status === "active") throw biz("an objective needs 2..5 key results to be active", { reason: "kr_count", min: MIN_KR, max: MAX_KR });
  const pillar = oneOf(b, "pillar", PILLARS) as Pillar | null;
  const at = nowIso();
  const o: MObjective = { ...base(newGoalId("objective"), at), source: "MANUAL", title: str(b, "title", true)!, owner_id: str(b, "owner_id", true)!, period_key: period,
    parent_id: parent, level: oneOf(b, "level", LEVELS, "department")!, okr_type: oneOf(b, "okr_type", ["committed", "aspirational"] as const, "committed")!,
    weight_pct: num(b, "weight_pct", false) ?? 100, team_id: str(b, "team_id", false), department_id: pinDepartment(req.claims, str(b, "department_id", false), pillar),
    pillar, status, progress_pct: 0, score: null, source_document_id: str(b, "source_document_id", false), strategic_objective_id: so };
  goalStore().objectives.push(o);
  recordAudit(req.claims, "execution.objective_create", "objectives", o.id);
  return ok(objOut(o), 201);
}

function patchObj(req: MockRequest) {
  const o = getObj(req, "write");
  expectVersion(req, o.version);
  const b = body(req);
  if ("title" in b) o.title = str(b, "title", true)!;
  if ("okr_type" in b) o.okr_type = oneOf(b, "okr_type", ["committed", "aspirational"] as const)!;
  if ("status" in b) {
    const st = oneOf(b, "status", STATUSES)!;
    const n = krsOf(o.id).length;
    if (st === "active" && (n < MIN_KR || n > MAX_KR)) throw biz("an objective needs 2..5 key results to be active", { reason: "kr_count", min: MIN_KR, max: MAX_KR, count: n });
    o.status = st;
  }
  Object.assign(o, { version: o.version + 1, updated_at: nowIso() });
  recordAudit(req.claims, "execution.objective_update", "objectives", o.id);
  return ok(objOut(o));
}

function deleteObj(req: MockRequest) {
  const o = getObj(req, "write");
  if (liveObjs().some((x) => x.parent_id === o.id)) throw err(409, "CONFLICT_STATE", "objective has children", { reason: "has_children" });
  o.deleted = true;
  for (const k of krsOf(o.id)) k.deleted = true;
  recordAudit(req.claims, "execution.objective_delete", "objectives", o.id);
  return ok(null, 204);
}

function createKr(req: MockRequest) {
  requireIdem(req);
  const o = getObj(req, "write");
  if (krsOf(o.id).length >= MAX_KR) throw biz("at most 5 key results", { reason: "kr_count", max: MAX_KR });
  const b = body(req);
  const baseline = num(b, "baseline", true)!;
  const target = num(b, "target", true)!;
  const current = num(b, "current_value", false);
  const at = nowIso();
  const k: MKr = { ...base(newGoalId("key_result"), at), source: "MANUAL", objective_id: o.id, title: str(b, "title", true)!, metric_code: str(b, "metric_code", false),
    unit: str(b, "unit", true, 50)!, baseline, target, current_value: current, owner_id: str(b, "owner_id", true)!, status: oneOf(b, "status", STATUSES, "active")!,
    confidence: null, weight_pct: num(b, "weight_pct", false) ?? 0, progress_pct: krProgressPct(baseline, target, current), at_risk: false, at_risk_since: null,
    at_risk_reasons: [], last_checked_in_at: null };
  goalStore().krs.push(k);
  recomputeObjective(goalStore(), o.id);
  recordAudit(req.claims, "execution.key_result_create", "key_results", k.id);
  return ok(krOut(k), 201);
}

function patchKr(req: MockRequest) {
  const k = getKr(req, "write");
  expectVersion(req, k.version);
  const b = body(req);
  if ("current_value" in b || "confidence" in b) throw invalid("current_value" in b ? "current_value" : "confidence", "only via check-in");
  if ("title" in b) k.title = str(b, "title", true)!;
  if ("owner_id" in b) k.owner_id = str(b, "owner_id", true)!;
  if ("target" in b) k.target = num(b, "target", true)!;
  if ("baseline" in b) k.baseline = num(b, "baseline", true)!;
  if ("weight_pct" in b) k.weight_pct = num(b, "weight_pct", true)!;
  k.progress_pct = krProgressPct(k.baseline, k.target, k.current_value);
  Object.assign(k, { version: k.version + 1, updated_at: nowIso() });
  recomputeObjective(goalStore(), k.objective_id);
  recordAudit(req.claims, "execution.key_result_update", "key_results", k.id);
  return ok(krOut(k));
}

function deleteKr(req: MockRequest) {
  const k = getKr(req, "write");
  k.deleted = true;
  recomputeObjective(goalStore(), k.objective_id);
  recordAudit(req.claims, "execution.key_result_delete", "key_results", k.id);
  return ok(null, 204);
}

// ---------------------------------------------------------------- check-ins (EP-PRF-01/02/05/06)
function checkInOut(c: MCheckIn) {
  const s = goalStore();
  if (c.key_result_id) {
    const k = s.krs.find((x) => x.id === c.key_result_id);
    const m = s.krMeasurements.find((x) => x.check_in_id === c.id);
    return { ...c, target_type: "key_result" as const, target_title: k?.title ?? null, department_id: k ? krScope(k).department_id : null,
      kr_measurement: m ? { value: m.value, progress_pct: m.progress_pct, previous_progress_pct: m.previous_progress_pct } : null };
  }
  const k = s.kpis.find((x) => x.id === c.kpi_id);
  return { ...c, target_type: "kpi" as const, target_title: k?.name ?? null, department_id: k?.department_id ?? null, kr_measurement: null };
}
const desc = (rows: MCheckIn[]) => [...rows].sort((a, b) => b.checked_in_at.localeCompare(a.checked_in_at));

function krCheckIns(req: MockRequest) {
  const k = getKr(req);
  return paginate(desc(goalStore().checkIns.filter((c) => c.key_result_id === k.id)).map(checkInOut) as unknown as Record<string, unknown>[], parsePage(req.query, ["checked_in_at"]));
}

function krMeasurements(req: MockRequest) {
  const k = getKr(req);
  const rows = goalStore().krMeasurements.filter((m) => m.key_result_id === k.id).sort((a, b) => b.measured_at.localeCompare(a.measured_at));
  return paginate(rows as unknown as Record<string, unknown>[], parsePage(req.query, ["measured_at"]));
}

function createKrCheckIn(req: MockRequest) {
  requireIdem(req);
  const k = getKr(req);
  if (!canCheckIn(req.claims, krScope(k))) throw forbiddenScope("key result");
  const b = parseCheckIn(req);
  const s = goalStore();
  const o = s.objectives.find((x) => x.id === k.objective_id)!;
  if (o.status !== "active") throw err(409, "CONFLICT_STATE", "objective is not active", { reason: "objective_not_active" });
  const { checkIn, becameAtRisk } = checkInKr(s, k, b, req.claims.sub, nowIso());
  recordAudit(req.claims, "execution.check_in_create", "check_ins", checkIn.id);
  if (becameAtRisk) {
    notifyGoalAlert({ ownerId: k.owner_id, departmentId: o.department_id, title: k.title, link: `/goals/objectives/${o.id}?kr=${k.id}`, refTable: "key_results", refId: k.id, actorId: req.claims.sub });
  }
  return ok(checkInOut(checkIn), 201);
}

function targetScope(c: MCheckIn): Scoped | null {
  const s = goalStore();
  if (c.key_result_id) {
    const k = s.krs.find((x) => x.id === c.key_result_id && !x.deleted);
    return k ? krScope(k) : null;
  }
  const k = s.kpis.find((x) => x.id === c.kpi_id && !x.deleted);
  return k ?? null;
}

function feed(req: MockRequest) {
  const q = req.query;
  const from = q.get("from");
  const to = q.get("to");
  if (from && to && from > to) throw err(400, "BAD_REQUEST", "from must be ≤ to", { param: "from" });
  const s = goalStore();
  const period = q.get("period_key");
  const rows = desc(s.checkIns).filter((c) => {
    const sc = targetScope(c);
    if (!sc || !(canRead(req.claims, sc) || c.user_id === req.claims.sub)) return false;
    const out = checkInOut(c);
    const day = c.checked_in_at.slice(0, 10);
    const krPeriod = c.key_result_id ? s.objectives.find((o) => o.id === s.krs.find((k) => k.id === c.key_result_id)?.objective_id)?.period_key : null;
    return (!q.get("owner_id") || c.user_id === q.get("owner_id")) && (!q.get("kpi_id") || c.kpi_id === q.get("kpi_id"))
      && (!q.get("key_result_id") || c.key_result_id === q.get("key_result_id")) && (!q.get("department_id") || out.department_id === q.get("department_id"))
      && (!q.get("confidence") || c.confidence === q.get("confidence")) && (!from || day >= from) && (!to || day <= to)
      && (!period || krPeriod === period || (c.kpi_id !== null && periodKeyFor("MONTH", day) === period));
  });
  return paginate(rows.map(checkInOut) as unknown as Record<string, unknown>[], parsePage(q, ["checked_in_at"]));
}

/** EP-PRF-06 — the caller's F4 cards: KR (Objective active, period contains today) + active KPI owned by the caller. */
function due(req: MockRequest) {
  const s = goalStore();
  const today = workToday();
  const me = req.claims.sub;
  const krCards = liveKrs().filter((k) => k.owner_id === me && k.status === "active").flatMap((k) => {
    const o = s.objectives.find((x) => x.id === k.objective_id && !x.deleted);
    const b = o ? periodBounds(o.period_key) : null;
    if (!o || o.status !== "active" || !b || today < b[0] || today >= b[1]) return [];
    const age = k.last_checked_in_at ? daysBetween(k.last_checked_in_at, today) : Number.POSITIVE_INFINITY;
    return [{ target_type: "key_result" as const, target_id: k.id, title: k.title, unit: k.unit, current_value: k.current_value, target: k.target,
      confidence: (k.confidence as "HIGH" | "MEDIUM" | "LOW" | null), last_checked_in_at: k.last_checked_in_at, due: age > KR_CHECKIN_MAX_AGE_DAYS, prefill: null }];
  });
  const kpiCards = s.kpis.filter((k) => !k.deleted && k.owner_id === me && k.status === "active").map((k) => {
    const cur = periodKeyFor(k.period_type === "ROLLING_12M" ? "MONTH" : k.period_type, today);
    const prevStart = periodBounds(cur)![0];
    const prev = periodKeyFor(k.period_type === "ROLLING_12M" ? "MONTH" : k.period_type, new Date(Date.parse(`${prevStart}T00:00:00Z`) - 86_400_000).toISOString().slice(0, 10));
    const last = s.measurements.filter((m) => m.kpi_id === k.id).sort((a, b) => b.measured_at.localeCompare(a.measured_at))[0];
    const lastCi = desc(s.checkIns.filter((c) => c.kpi_id === k.id))[0];
    const ci = lastCi?.confidence;
    return { target_type: "kpi" as const, target_id: k.id, title: k.name, unit: k.unit, current_value: last?.actual_value ?? null, target: k.target,
      confidence: (ci === "HIGH" || ci === "MEDIUM" || ci === "LOW" ? ci : null), last_checked_in_at: lastCi?.checked_in_at ?? null,
      due: !s.measurements.some((m) => m.kpi_id === k.id && m.period_key === prev), prefill: null };
  });
  return ok([...krCards, ...kpiCards].sort((a, b) => Number(b.due) - Number(a.due)));
}

const R = "execution:read";
const W = "execution:write";
export const OKR_ROUTES: readonly Route[] = [
  { method: "GET", pattern: "/objectives", permission: R, handler: listObjs },
  { method: "POST", pattern: "/objectives", permission: W, handler: createObj },
  { method: "GET", pattern: "/objectives/:id", permission: R, handler: (req) => ok(objOut(getObj(req))) },
  { method: "PATCH", pattern: "/objectives/:id", permission: W, handler: patchObj },
  { method: "DELETE", pattern: "/objectives/:id", permission: W, handler: deleteObj },
  { method: "GET", pattern: "/objectives/:id/key-results", permission: R, handler: (req) => {
    const o = getObj(req);
    const rows = krsOf(o.id).filter((k) => canRead(req.claims, krScope(k)));
    return ok(rows.map(krOut));
  } },
  { method: "POST", pattern: "/objectives/:id/key-results", permission: W, handler: createKr },
  { method: "GET", pattern: "/key-results/:id", permission: R, handler: (req) => ok(krOut(getKr(req))) },
  { method: "PATCH", pattern: "/key-results/:id", permission: W, handler: patchKr },
  { method: "DELETE", pattern: "/key-results/:id", permission: W, handler: deleteKr },
  { method: "GET", pattern: "/key-results/:id/measurements", permission: R, handler: krMeasurements },
  { method: "GET", pattern: "/key-results/:id/check-ins", permission: R, handler: krCheckIns },
  { method: "POST", pattern: "/key-results/:id/check-ins", permission: W, handler: createKrCheckIn },
  { method: "GET", pattern: "/goals/check-ins", permission: R, handler: feed },
  { method: "GET", pattern: "/goals/check-ins/due", permission: R, handler: due },
];

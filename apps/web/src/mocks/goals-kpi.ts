/** Mock EP-KPI-01..10 + EP-PRF-03/04 (10 §7.2.3, R-DEC-51..53). */
import { recordAudit } from "./audit";
import { ok, paginate, parsePage } from "./http";
import type { MockRequest, Route } from "./router";
import { canCheckIn, canRead, canWrite, forbiddenRole, forbiddenScope, pinDepartment, requireManager } from "./goal-scope";
import { periodBounds, periodKeyFor, periodMatchesType } from "./goals-rules";
import { base, currentTarget, goalStore, latestEvaluation, measure, newGoalId, type MKpi, type MKpiTarget, type Pillar } from "./goals-store";
import { evaluationBrief } from "./goals-tree";
import { notifyGoalAlert } from "./goals-notify";
import { biz, body, CONFIDENCES, err, expectVersion, invalid, isDate, notFound, nowIso, num, oneOf, PILLARS, requireIdem, str, strip } from "./goals-http";
import { workStore, workToday } from "./work-store";

const DIRECTIONS = ["HIGHER_IS_BETTER", "LOWER_IS_BETTER", "WITHIN_RANGE", "BINARY"] as const;
const PERIOD_TYPES = ["MONTH", "QUARTER", "YEAR", "ROLLING_12M"] as const;
const DATA_SOURCES = ["manual", "document", "automated", "ai_assisted"] as const;
const LOW_BANDS = new Set(["BELOW", "CRITICAL"]);

const liveKpis = () => goalStore().kpis.filter((k) => !k.deleted);
export const kpiOut = (k: MKpi) => ({ ...strip(k), latest_evaluation: evaluationBrief(goalStore(), k.id) });

export function getKpi(req: MockRequest, action: "read" | "write" = "read"): MKpi {
  const k = liveKpis().find((x) => x.id === req.params.id);
  if (!k) throw notFound("kpi");
  if (!canRead(req.claims, k)) throw forbiddenScope("kpi");
  if (action === "write") {
    requireManager(req.claims, "write kpis");
    if (!canWrite(req.claims, k)) throw forbiddenScope("kpi");
  }
  return k;
}

function listKpis(req: MockRequest) {
  const q = req.query;
  const s = goalStore();
  const eq = (f: "owner_id" | "metric_code" | "strategic_objective_id" | "department_id" | "parent_kpi_id", k: MKpi) => !q.get(f) || k[f] === q.get(f);
  const bandQ = q.get("band");
  const rows = liveKpis().filter((k) => canRead(req.claims, k) && eq("owner_id", k) && eq("metric_code", k) && eq("strategic_objective_id", k) && eq("department_id", k)
    && eq("parent_kpi_id", k) && (!bandQ || latestEvaluation(s, k.id)?.band === bandQ));
  return paginate(rows.map(kpiOut) as unknown as Record<string, unknown>[], parsePage(q, ["code", "name", "updated_at"]));
}

function createKpi(req: MockRequest) {
  requireIdem(req);
  requireManager(req.claims, "create kpis");
  const b = body(req);
  const code = str(b, "code", true, 50)!;
  if (liveKpis().some((k) => k.code === code)) throw err(409, "DUPLICATE_RESOURCE", "kpi code exists", { field: "code" });
  const parent = str(b, "parent_kpi_id", false);
  const so = str(b, "strategic_objective_id", false);
  if (parent && so) throw biz("only root KPIs link a strategic objective", { field: "strategic_objective_id" });
  if (so && !goalStore().sos.some((x) => !x.deleted && x.id === so)) throw biz("strategic objective not found", { field: "strategic_objective_id" });
  const pillar = oneOf(b, "pillar", PILLARS) as Pillar | null;
  const at = nowIso();
  const k: MKpi = { ...base(newGoalId("kpi"), at), source: "MANUAL", code, name: str(b, "name", true)!, unit: str(b, "unit", true, 50)!, target: num(b, "target", true)!,
    owner_id: str(b, "owner_id", true)!, metric_code: str(b, "metric_code", false), key_result_id: str(b, "key_result_id", false),
    period_type: oneOf(b, "period_type", PERIOD_TYPES, "MONTH")!, direction: oneOf(b, "direction", DIRECTIONS, "HIGHER_IS_BETTER")!, value_type: "numeric",
    data_source_kind: oneOf(b, "data_source_kind", DATA_SOURCES, "manual")!, parent_kpi_id: parent, weight_pct: num(b, "weight_pct", false) ?? 100,
    initiative_id: str(b, "initiative_id", false), department_id: pinDepartment(req.claims, str(b, "department_id", false), pillar),
    status: oneOf(b, "status", ["draft", "active", "closed"] as const, "active")!, strategic_objective_id: so, pillar };
  goalStore().kpis.push(k);
  recordAudit(req.claims, "execution.kpi_create", "kpis", k.id);
  return ok(kpiOut(k), 201);
}

function patchKpi(req: MockRequest) {
  const k = getKpi(req, "write");
  expectVersion(req, k.version);
  const b = body(req);
  for (const f of ["name", "unit", "owner_id"] as const) if (f in b) k[f] = str(b, f, true)!;
  if ("target" in b) k.target = num(b, "target", true)!;
  if ("direction" in b) k.direction = oneOf(b, "direction", DIRECTIONS)!;
  if ("status" in b) k.status = oneOf(b, "status", ["draft", "active", "closed"] as const)!;
  Object.assign(k, { version: k.version + 1, updated_at: nowIso() });
  recordAudit(req.claims, "execution.kpi_update", "kpis", k.id);
  return ok(kpiOut(k));
}

function deleteKpi(req: MockRequest) {
  const k = getKpi(req, "write");
  if (liveKpis().some((x) => x.parent_kpi_id === k.id)) throw err(409, "CONFLICT_STATE", "kpi has children", { reason: "has_children" });
  if (workStore().tasks.some((t) => !t.deleted && t.kpi_id === k.id)) throw err(409, "CONFLICT_STATE", "kpi has tasks", { reason: "has_tasks" });
  k.deleted = true;
  recordAudit(req.claims, "execution.kpi_delete", "kpis", k.id);
  return ok(null, 204);
}

// ---------------------------------------------------------------- measurements / targets / evaluations
function listMeasurements(req: MockRequest) {
  const k = getKpi(req);
  const p = req.query.get("period_key");
  const rows = goalStore().measurements.filter((m) => m.kpi_id === k.id && (!p || m.period_key === p));
  return paginate(rows as unknown as Record<string, unknown>[], parsePage(req.query, ["measured_at", "period_key"]));
}

/** Target hiệu lực at `day`, else a target auto-created from `kpis.target_value` (v2.1 behaviour). */
function targetFor(k: MKpi, period: string, day: string): MKpiTarget {
  const s = goalStore();
  const t = currentTarget(s, k.id, period, day);
  if (t) return t;
  const b = periodBounds(period)!;
  const row: MKpiTarget = { ...base(newGoalId("kpi_target")), source: "SYSTEM", kpi_id: k.id, period_key: period, baseline: null, minimum: null, target: k.target, stretch: null,
    band_thresholds: {}, score_cap_pct: 150, locked_at: null, valid_from: b[0], valid_to: null, reason: null };
  s.targets.push(row);
  return row;
}

export function recordMeasurement(req: MockRequest, k: MKpi, o: { period: string; value: number; note: string | null; dataSource: string; sourceDocumentId: string | null; checkInId: string | null }) {
  if (!periodMatchesType(o.period, k.period_type)) throw biz("period_key does not match period_type", { field: "period_key", period_type: k.period_type });
  const s = goalStore();
  const day = workToday();
  const t = targetFor(k, o.period, day);
  if (t.locked_at) throw err(409, "CONFLICT_STATE", "period is locked", { reason: "period_locked" });
  const before = latestEvaluation(s, k.id);
  const prevBand = s.evaluations.find((e) => !e.deleted && e.kpi_id === k.id && e.period_key === o.period)?.band ?? before?.band ?? null;
  const m = measure(s, k, t, { period_key: o.period, actual_value: o.value, measured_at: nowIso(), measured_by: req.claims.sub, data_source: o.dataSource, note: o.note,
    check_in_id: o.checkInId, source_document_id: o.sourceDocumentId });
  recordAudit(req.claims, "execution.kpi_measure", "kpi_measurements", m.id);
  // execution.kpi_below_threshold: only when the band moves into BELOW/CRITICAL
  if (LOW_BANDS.has(m.evaluation_band) && !(prevBand && LOW_BANDS.has(prevBand))) {
    notifyGoalAlert({ ownerId: k.owner_id, departmentId: k.department_id, title: `${k.code} — ${k.name}`, link: `/goals/kpis/${k.id}`, refTable: "kpis", refId: k.id, actorId: req.claims.sub });
  }
  return m;
}

function createMeasurement(req: MockRequest) {
  requireIdem(req);
  const k = getKpi(req);
  if (!canCheckIn(req.claims, k)) throw forbiddenScope("kpi");
  const b = body(req);
  const period = str(b, "period_key", true, 10)!;
  const m = recordMeasurement(req, k, { period, value: num(b, "actual_value", true)!, note: str(b, "note", false, 5000), dataSource: oneOf(b, "data_source", DATA_SOURCES, "manual")!,
    sourceDocumentId: str(b, "source_document_id", false), checkInId: null });
  return ok(m, 201);
}

function listTargets(req: MockRequest) {
  const k = getKpi(req);
  const p = req.query.get("period_key");
  const asOf = req.query.get("as_of");
  if (asOf && !isDate(asOf)) throw err(400, "BAD_REQUEST", "as_of must be YYYY-MM-DD", { param: "as_of" });
  const rows = goalStore().targets.filter((t) => !t.deleted && t.kpi_id === k.id && (!p || t.period_key === p) && (!asOf || (t.valid_from <= asOf && (t.valid_to === null || asOf < t.valid_to))))
    .sort((a, b) => a.period_key.localeCompare(b.period_key) || a.valid_from.localeCompare(b.valid_from));
  return paginate(rows.map(strip) as unknown as Record<string, unknown>[], parsePage(req.query, ["period_key", "valid_from"]));
}

/** EP-KPI-09: close the current target of the period + open a new one (R-DEC-52), then re-evaluate. */
function createTarget(req: MockRequest) {
  requireIdem(req);
  if (req.claims.role === "EMP") throw forbiddenRole("set kpi targets");
  const k = getKpi(req, "write");
  const b = body(req);
  const period = str(b, "period_key", true, 10)!;
  if (!periodMatchesType(period, k.period_type)) throw biz("period_key does not match period_type", { field: "period_key" });
  const [start, end] = periodBounds(period)!;
  const from = (b.valid_from as string | undefined) ?? workToday();
  if (!isDate(from)) throw invalid("valid_from");
  const s = goalStore();
  const cur = currentTarget(s, k.id, period);
  if (cur?.locked_at) throw err(409, "CONFLICT_STATE", "period is locked", { reason: "period_locked" });
  if (from < start || from >= end) throw biz("valid_from outside the period", { field: "valid_from" });
  if (cur && from <= cur.valid_from) throw biz("valid_from must be after the current target", { field: "valid_from" });
  const at = nowIso();
  if (cur) Object.assign(cur, { valid_to: from, version: cur.version + 1, updated_at: at });
  const t: MKpiTarget = { ...base(newGoalId("kpi_target"), at), source: "MANUAL", kpi_id: k.id, period_key: period, baseline: num(b, "baseline", false), minimum: num(b, "minimum", false),
    target: num(b, "target", true)!, stretch: num(b, "stretch", false), band_thresholds: (b.band_thresholds as Record<string, number> | null) ?? {}, score_cap_pct: num(b, "score_cap_pct", false) ?? 150,
    locked_at: null, valid_from: from, valid_to: null, reason: str(b, "reason", false, 1000) };
  s.targets.push(t);
  const last = s.measurements.filter((m) => m.kpi_id === k.id && m.period_key === period).at(-1);
  if (last) measure(s, k, t, { ...last, measured_at: last.measured_at });
  recordAudit(req.claims, "execution.kpi_target_set", "kpi_targets", t.id, t.reason);
  return ok(strip(t), 201);
}

function listEvaluations(req: MockRequest) {
  const k = getKpi(req);
  const from = req.query.get("from_period");
  const to = req.query.get("to_period");
  let rows = goalStore().evaluations.filter((e) => !e.deleted && e.kpi_id === k.id && (!from || e.period_key >= from) && (!to || e.period_key <= to))
    .sort((a, b) => a.period_key.localeCompare(b.period_key));
  if (!from && !to) rows = rows.slice(-12);
  return ok(rows.map(strip));
}

// ---------------------------------------------------------------- EP-PRF-03/04
export interface ParsedCheckIn { value: number; confidence: "HIGH" | "MEDIUM" | "LOW"; note: string | null; blocker: string | null; support_needed: string | null; next_action: string | null }
export function parseCheckIn(req: MockRequest): ParsedCheckIn {
  const b = body(req);
  const confidence = oneOf(b, "confidence", CONFIDENCES);
  if (!confidence) throw invalid("confidence", "confidence is required");
  return { value: num(b, "value", true)!, confidence, note: str(b, "note", false, 5000), blocker: str(b, "blocker", false, 5000),
    support_needed: str(b, "support_needed", false, 5000), next_action: str(b, "next_action", false, 5000) };
}

function kpiCheckIns(req: MockRequest) {
  const k = getKpi(req);
  const rows = goalStore().checkIns.filter((c) => c.kpi_id === k.id).sort((a, b) => b.checked_in_at.localeCompare(a.checked_in_at));
  return paginate(rows.map((c) => ({ ...c, target_type: "kpi", target_title: k.name, department_id: k.department_id, kr_measurement: null })) as unknown as Record<string, unknown>[], parsePage(req.query, ["checked_in_at"]));
}

function createKpiCheckIn(req: MockRequest) {
  requireIdem(req);
  const k = getKpi(req);
  if (!canCheckIn(req.claims, k)) throw forbiddenScope("kpi");
  const b = parseCheckIn(req);
  const s = goalStore();
  const at = nowIso();
  const ci = { id: newGoalId("check_in"), created_at: at, key_result_id: null, kpi_id: k.id, ...b, checked_in_at: at, user_id: req.claims.sub };
  const period = periodKeyFor(k.period_type === "ROLLING_12M" ? "MONTH" : k.period_type, workToday());
  recordMeasurement(req, k, { period, value: b.value, note: b.note, dataSource: "manual", sourceDocumentId: null, checkInId: ci.id });
  s.checkIns.push(ci);
  recordAudit(req.claims, "execution.check_in_create", "check_ins", ci.id);
  return ok({ ...ci, target_type: "kpi", target_title: k.name, department_id: k.department_id, kr_measurement: null }, 201);
}

const R = "execution:read";
const W = "execution:write";
export const KPI_ROUTES: readonly Route[] = [
  { method: "GET", pattern: "/kpis", permission: R, handler: listKpis },
  { method: "POST", pattern: "/kpis", permission: W, handler: createKpi },
  { method: "GET", pattern: "/kpis/:id", permission: R, handler: (req) => ok(kpiOut(getKpi(req))) },
  { method: "PATCH", pattern: "/kpis/:id", permission: W, handler: patchKpi },
  { method: "DELETE", pattern: "/kpis/:id", permission: W, handler: deleteKpi },
  { method: "GET", pattern: "/kpis/:id/measurements", permission: R, handler: listMeasurements },
  { method: "POST", pattern: "/kpis/:id/measurements", permission: W, handler: createMeasurement },
  { method: "GET", pattern: "/kpis/:id/targets", permission: R, handler: listTargets },
  { method: "POST", pattern: "/kpis/:id/targets", permission: W, handler: createTarget },
  { method: "GET", pattern: "/kpis/:id/evaluations", permission: R, handler: listEvaluations },
  { method: "GET", pattern: "/kpis/:id/check-ins", permission: R, handler: kpiCheckIns },
  { method: "POST", pattern: "/kpis/:id/check-ins", permission: W, handler: createKpiCheckIn },
];

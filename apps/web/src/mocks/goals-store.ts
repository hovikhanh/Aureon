/**
 * Mock D07–D10 goals store (T-626F/T-627F/T-628F, 10 §7.2.3, 05 §2.6). Seeded from
 * `seed_snapshot.json` (`kpis`, `okrs`, `projects`) the way `execution_seed.py` writes them. The
 * M1.4 snapshot (T-631: strategies / SO / initiatives / check-ins / evaluations) does not exist
 * yet → **mock-only** rows are built here: 1 Strategy, 4 SO (C/F/U/O), INI-01..04 (`exec_data`),
 * Project ↔ Initiative links, KPIEvaluation per measured period, ~10 check-ins + KRMeasurement
 * (UC-04 KR 2,58 → 2,52 LOW = at-risk) and the EMP demo account as owner of one KR + one KPI.
 * Every snapshot field is optional-safe. One shared store per process (like `work-store.ts`).
 */
import { SNAPSHOT, mockId, type MockClaims } from "./fixtures";
import { WORK_STAMP, workToday } from "./work-store";
import {
  achievementPct, atRisk, bandOf, gapValue, krProgressPct, periodBounds, weightedAvg, type AtRiskReason, type Band,
} from "./goals-rules";

export type Pillar = "F" | "O" | "C" | "U" | "S";
const dId = (code: string) => mockId("department", code);
const uId = (email: string) => mockId("user", email);
const userOf = (role: string, dept?: string) => SNAPSHOT.users.find((u) => u.role === role && (!dept || u.department === dept));
export const CEO_UID = uId(userOf("CEO")?.email ?? "ceo");

interface Base { id: string; version: number; source: string; data_classification: string; created_at: string; updated_at: string; deleted: boolean }
export interface MStrategy extends Base { code: string; name: string; vision: string | null; mission: string | null; period_start: string; period_end: string; owner_id: string; status: string }
export interface MSO extends Base { strategy_id: string; code: string; title: string; description: string | null; pillar: Pillar | null; owner_id: string; department_id: string | null; weight_pct: number; sort_order: number; status: string; progress_pct: number }
export interface MKpi extends Base {
  code: string; name: string; unit: string; target: number; owner_id: string; metric_code: string | null; key_result_id: string | null; period_type: string;
  direction: string; value_type: string; data_source_kind: string; parent_kpi_id: string | null; weight_pct: number; initiative_id: string | null;
  department_id: string | null; status: string; strategic_objective_id: string | null; pillar: Pillar | null;
}
export interface MKpiTarget extends Base { kpi_id: string; period_key: string; baseline: number | null; minimum: number | null; target: number; stretch: number | null; band_thresholds: Record<string, number>; score_cap_pct: number; locked_at: string | null; valid_from: string; valid_to: string | null; reason: string | null }
export interface MMeasurement { id: string; created_at: string; kpi_id: string; period_key: string; actual_value: number; achievement_pct: number; evaluation_band: string; kpi_target_id: string; locked_at: string | null; measured_at: string; source_document_id: string | null; measured_by: string | null; data_source: string; note: string | null; check_in_id: string | null }
export interface MEvaluation extends Base { kpi_id: string; period_key: string; kpi_target_id: string; measurement_id: string; actual_value: number; target: number; achievement_pct: number; band: Band; previous_band: Band | null; gap_value: number; measured_on_time: boolean; evaluated_at: string; locked_at: string | null }
export interface MObjective extends Base { title: string; owner_id: string; period_key: string; parent_id: string | null; level: string; okr_type: string; weight_pct: number; team_id: string | null; department_id: string | null; pillar: Pillar | null; status: string; progress_pct: number; score: number | null; source_document_id: string | null; strategic_objective_id: string | null }
export interface MKr extends Base { objective_id: string; title: string; metric_code: string | null; unit: string; baseline: number; target: number; current_value: number | null; owner_id: string; status: string; confidence: string | null; weight_pct: number; progress_pct: number; at_risk: boolean; at_risk_since: string | null; at_risk_reasons: AtRiskReason[]; last_checked_in_at: string | null }
export interface MKrMeasurement { id: string; created_at: string; key_result_id: string; check_in_id: string | null; period_key: string; value: number; progress_pct: number; previous_progress_pct: number | null; confidence: "HIGH" | "MEDIUM" | "LOW"; measured_at: string; measured_by: string | null }
export interface MCheckIn { id: string; created_at: string; key_result_id: string | null; kpi_id: string | null; value: number; confidence: string; note: string | null; blocker: string | null; support_needed: string | null; next_action: string | null; checked_in_at: string; user_id: string }
export interface MInitiative extends Base { code: string; title: string; description: string | null; objective_id: string | null; strategic_objective_id: string | null; pillar: Pillar | null; owner_id: string; department_id: string | null; start_date: string; planned_end_date: string; status: string; progress_pct: number; weight_pct: number; budget_amount: number | null; currency: string; project_codes: string[] }
export interface GoalStore {
  strategies: MStrategy[]; sos: MSO[]; kpis: MKpi[]; targets: MKpiTarget[]; measurements: MMeasurement[]; evaluations: MEvaluation[];
  objectives: MObjective[]; krs: MKr[]; krMeasurements: MKrMeasurement[]; checkIns: MCheckIn[]; initiatives: MInitiative[]; seq: number;
}

const G = globalThis as typeof globalThis & { __aureonMockGoals?: GoalStore | null };
export function goalStore(): GoalStore {
  G.__aureonMockGoals ??= seedGoals();
  return G.__aureonMockGoals;
}
export function resetGoalStore(): void {
  G.__aureonMockGoals = null;
}
export const newGoalId = (kind: string) => mockId(kind, `new-${++goalStore().seq}-${Date.now()}`);
export const base = (id: string, at = WORK_STAMP): Base => ({ id, version: 1, source: "SEED", data_classification: "internal", created_at: at, updated_at: at, deleted: false });

// ------------------------------------------------------------------------------------ seed
type SnapKpi = { code: string; name: string; department?: string | null; direction?: string; unit?: string; target?: number; measurements?: Record<string, number>; parent?: string | null };
type SnapKr = { title: string; unit?: string; baseline?: number; target?: number; current?: number; confidence?: string };
type SnapOkr = { code: string; title: string; department?: string | null; period_key?: string; key_results?: SnapKr[] };
type SnapSo = { code: string; title: string; pillar: Pillar; department: string; owner: string; weight_pct: number; kpis: string[]; objectives: string[]; initiative: string; projects: string[] };
type SnapIni = { code: string; title: string; pillar: Pillar; department: string; start_date: string; planned_end_date: string; progress_pct: number; weight_pct: number };
type SnapCheckIn = { okr: string; key_result: number; value: number; confidence: "HIGH" | "MEDIUM" | "LOW"; date: string; by: string; note: string | null };
type SnapStrategy = { code: string; name: string; period_start: string; period_end: string; strategic_objectives: SnapSo[] };
const SNAP = SNAPSHOT as unknown as { kpis?: SnapKpi[]; okrs?: SnapOkr[]; strategy?: SnapStrategy; initiatives?: SnapIni[]; check_ins?: SnapCheckIn[]; reference_date?: string };
/** `goals_seed.REFERENCE` — seed at-risk flags are evaluated on this day (not on the wall clock). */
const SEED_DAY = SNAP.reference_date ?? "2026-10-20";
const OKR_PERIOD = "2026-Q4";
export const UC04_KR = "OKR-SAL:1";
/** employee@ owns KR OKR-SVC #1 through its seed check-in (`exec_data.CHECK_INS`). */
export const EMP_KR = "OKR-SVC:1";
export const soId = (code: string) => mockId("strategic_objective", code);
export const kpiId = (code: string) => mockId("kpi", code);
export const objId = (code: string) => mockId("objective", code);
export const krId = (key: string) => mockId("key_result", key);
export const iniId = (code: string) => mockId("initiative", code);
export const STRATEGY_ID = mockId("strategy", SNAP.strategy?.code ?? "STR");
/** `checked_at(day)`: 09:00 Asia/Ho_Chi_Minh = 02:00Z. */
const checkedAt = (day: string) => `${day}T02:00:00Z`;

/** Mirror of `goals_seed.seed_goals` over the snapshot: KPI / Objective owners = CEO, KR owner = author of its seed check-in. */
function seedGoals(): GoalStore {
  const s: GoalStore = { strategies: [], sos: [], kpis: [], targets: [], measurements: [], evaluations: [], objectives: [], krs: [], krMeasurements: [], checkIns: [], initiatives: [], seq: 0 };
  const st = SNAP.strategy;
  for (const k of SNAP.kpis ?? []) seedKpi(s, k);
  for (const o of SNAP.okrs ?? []) seedOkr(s, o);
  if (st) {
    s.strategies.push({ ...base(STRATEGY_ID), code: st.code, name: st.name, vision: null, mission: null, period_start: st.period_start, period_end: st.period_end, owner_id: CEO_UID, status: "active" });
    st.strategic_objectives.forEach((so, i) => {
      const id = soId(so.code);
      s.sos.push({ ...base(id), strategy_id: STRATEGY_ID, code: so.code, title: so.title, description: null, pillar: so.pillar, owner_id: uId(so.owner),
        department_id: dId(so.department), weight_pct: so.weight_pct, sort_order: i, status: "active", progress_pct: 0 });
      const ini = (SNAP.initiatives ?? []).find((x) => x.code === so.initiative);
      if (ini) s.initiatives.push({ ...base(iniId(ini.code)), code: ini.code, title: ini.title, description: null, objective_id: so.objectives[0] ? objId(so.objectives[0]) : null,
        strategic_objective_id: id, pillar: ini.pillar, owner_id: CEO_UID, department_id: dId(ini.department), start_date: ini.start_date, planned_end_date: ini.planned_end_date,
        status: "active", progress_pct: ini.progress_pct, weight_pct: ini.weight_pct, budget_amount: null, currency: "VND", project_codes: so.projects });
      for (const k of s.kpis) if (so.kpis.includes(k.code)) Object.assign(k, { strategic_objective_id: id, pillar: so.pillar });
      for (const o of s.objectives) if (so.objectives.some((c) => objId(c) === o.id)) Object.assign(o, { strategic_objective_id: id, pillar: so.pillar });
    });
  }
  seedCheckIns(s);
  seedAtRisk(s);
  for (const so of s.sos) recomputeSo(s, so);
  return s;
}

function seedKpi(s: GoalStore, k: SnapKpi): void {
  const id = kpiId(k.code);
  const dept = k.department ?? null;
  const parent = k.parent ?? null;
  const target = k.target ?? 0;
  const direction = k.direction ?? "HIGHER_IS_BETTER";
  s.kpis.push({ ...base(id), code: k.code, name: k.name, unit: k.unit ?? "", target, owner_id: CEO_UID, metric_code: null,
    key_result_id: null, period_type: "MONTH", direction, value_type: "numeric", data_source_kind: "manual", parent_kpi_id: parent ? kpiId(parent) : null,
    weight_pct: 100, initiative_id: null, department_id: dept ? dId(dept) : null, status: "active",
    strategic_objective_id: null, pillar: null });
  for (const [period, actual] of Object.entries(k.measurements ?? {})) {
    const b = periodBounds(period);
    if (!b) continue;
    s.targets.push(target_(id, period, target, b[0], null, null, "open"));
    const t = currentTarget(s, id, period)!;
    measure(s, s.kpis.at(-1)!, t, { period_key: period, actual_value: actual, measured_at: `${period}-28T03:00:00Z`, measured_by: null, data_source: "manual", note: null, check_in_id: null, source_document_id: null });
  }
}

function target_(kpi: string, period: string, target: number, from: string, to: string | null, reason: string | null, tag: string): MKpiTarget {
  return { ...base(mockId("kpi_target", `${kpi}:${period}:${tag}`)), kpi_id: kpi, period_key: period, baseline: null, minimum: null, target, stretch: null,
    band_thresholds: {}, score_cap_pct: 150, locked_at: null, valid_from: from, valid_to: to, reason };
}

export function currentTarget(s: GoalStore, kpi: string, period: string, day?: string): MKpiTarget | undefined {
  const rows = s.targets.filter((t) => !t.deleted && t.kpi_id === kpi && t.period_key === period);
  if (!day) return rows.find((t) => t.valid_to === null);
  return rows.find((t) => t.valid_from <= day && (t.valid_to === null || day < t.valid_to)) ?? rows.find((t) => t.valid_to === null);
}

const KPI_GRACE_DAYS = 5;
/** EP-KPI-07 core: INSERT a measurement (R-DEC-51) + upsert KPIEvaluation of the period (R-DEC-53). */
export function measure(s: GoalStore, kpi: MKpi, t: MKpiTarget, m: Omit<MMeasurement, "id" | "created_at" | "kpi_id" | "achievement_pct" | "evaluation_band" | "kpi_target_id" | "locked_at">): MMeasurement {
  const ach = achievementPct(kpi.direction, m.actual_value, t.target, t.minimum, t.score_cap_pct);
  const band = bandOf(ach, Object.keys(t.band_thresholds).length ? t.band_thresholds : undefined);
  const row: MMeasurement = { ...m, id: mockId("kpi_measurement", `${kpi.id}:${m.period_key}:${s.measurements.length}`), created_at: m.measured_at, kpi_id: kpi.id,
    achievement_pct: ach, evaluation_band: band, kpi_target_id: t.id, locked_at: null };
  s.measurements.push(row);
  const end = periodBounds(m.period_key)?.[1] ?? m.measured_at;
  const graceEnd = new Date(Date.parse(`${end}T00:00:00Z`) + KPI_GRACE_DAYS * 86_400_000).toISOString();
  const prev = s.evaluations.find((e) => !e.deleted && e.kpi_id === kpi.id && e.period_key === m.period_key);
  const evalRow: MEvaluation = {
    ...(prev ?? base(mockId("kpi_evaluation", `${kpi.id}:${m.period_key}`), m.measured_at)), kpi_id: kpi.id, period_key: m.period_key, kpi_target_id: t.id,
    measurement_id: row.id, actual_value: m.actual_value, target: t.target, achievement_pct: ach, band, previous_band: prev ? prev.band : previousPeriodBand(s, kpi.id, m.period_key),
    gap_value: gapValue(kpi.direction, m.actual_value, t.target), measured_on_time: m.measured_at < graceEnd, evaluated_at: m.measured_at, locked_at: null,
  };
  if (prev) { Object.assign(prev, evalRow, { version: prev.version + 1, updated_at: m.measured_at }); } else s.evaluations.push(evalRow);
  return row;
}
function previousPeriodBand(s: GoalStore, kpi: string, period: string): Band | null {
  const older = s.evaluations.filter((e) => !e.deleted && e.kpi_id === kpi && e.period_key < period).sort((a, b) => b.period_key.localeCompare(a.period_key));
  return older[0]?.band ?? null;
}
export function latestEvaluation(s: GoalStore, kpi: string): MEvaluation | undefined {
  return s.evaluations.filter((e) => !e.deleted && e.kpi_id === kpi).sort((a, b) => b.period_key.localeCompare(a.period_key))[0];
}

function seedOkr(s: GoalStore, o: SnapOkr): void {
  const oid = objId(o.code);
  const dept = o.department ?? null;
  s.objectives.push({ ...base(oid), title: o.title, owner_id: CEO_UID, period_key: o.period_key ?? OKR_PERIOD, parent_id: null, level: dept ? "department" : "company",
    okr_type: "committed", weight_pct: 100, team_id: null, department_id: dept ? dId(dept) : null, pillar: null, status: "active",
    progress_pct: 0, score: null, source_document_id: null, strategic_objective_id: null });
  const krs = o.key_results ?? [];
  krs.forEach((kr, i) => {
    const key = `${o.code}:${i}`;
    const baseline = kr.baseline ?? 0;
    const target = kr.target ?? 0;
    const current = kr.current ?? null;
    s.krs.push({ ...base(krId(key)), objective_id: oid, title: kr.title, metric_code: null, unit: kr.unit ?? "", baseline, target, current_value: current,
      owner_id: CEO_UID, status: "active", confidence: kr.confidence ?? null,
      weight_pct: Math.round((100 / krs.length) * 100) / 100, progress_pct: krProgressPct(baseline, target, current), at_risk: false, at_risk_since: null,
      at_risk_reasons: [], last_checked_in_at: null });
  });
  recomputeObjective(s, oid);
}

export function recomputeObjective(s: GoalStore, oid: string): void {
  const o = s.objectives.find((x) => x.id === oid);
  if (!o) return;
  o.progress_pct = weightedAvg(s.krs.filter((k) => !k.deleted && k.objective_id === oid).map((k) => [k.progress_pct, k.weight_pct] as const));
}
/** 05 §2.6: SO progress = weighted mean of live Initiatives; none → mean of direct Objectives; none → 0. */
export function recomputeSo(s: GoalStore, so: MSO): void {
  const inis = s.initiatives.filter((i) => !i.deleted && i.strategic_objective_id === so.id);
  if (inis.length) { so.progress_pct = weightedAvg(inis.map((i) => [i.progress_pct, i.weight_pct] as const)); return; }
  const objs = s.objectives.filter((o) => !o.deleted && o.strategic_objective_id === so.id);
  so.progress_pct = objs.length ? weightedAvg(objs.map((o) => [o.progress_pct, 0] as const)) : 0;
}

export interface CheckInBody { value: number; confidence: "HIGH" | "MEDIUM" | "LOW"; note: string | null; blocker: string | null; support_needed: string | null; next_action: string | null }
/** EP-PRF-02 core — one "transaction": CheckIn + KRMeasurement + KR update + at-risk (R-DEC-55) + Objective progress. */
export function checkInKr(s: GoalStore, kr: MKr, b: CheckInBody, userId: string, at: string, today = workToday()): { checkIn: MCheckIn; becameAtRisk: boolean; expectedPct: number } {
  const o = s.objectives.find((x) => x.id === kr.objective_id)!;
  const ci: MCheckIn = { id: mockId("check_in", `${kr.id}:${s.checkIns.length}:${at}`), created_at: at, key_result_id: kr.id, kpi_id: null, ...b, checked_in_at: at, user_id: userId };
  const progress = krProgressPct(kr.baseline, kr.target, b.value);
  // BE: previous = progress of the latest KRMeasurement (none → null), not the KR column
  const prev = s.krMeasurements.filter((m) => m.key_result_id === kr.id).sort((x, y) => y.measured_at.localeCompare(x.measured_at))[0]?.progress_pct ?? null;
  s.checkIns.push(ci);
  s.krMeasurements.push({ id: mockId("kr_measurement", ci.id), created_at: at, key_result_id: kr.id, check_in_id: ci.id, period_key: o.period_key, value: b.value,
    progress_pct: progress, previous_progress_pct: prev, confidence: b.confidence, measured_at: at, measured_by: userId });
  const risk = atRisk({ progress, previousProgress: prev, confidence: b.confidence, periodKey: o.period_key, today });
  const became = risk.at_risk && !kr.at_risk;
  Object.assign(kr, { current_value: b.value, confidence: b.confidence, progress_pct: progress, last_checked_in_at: at, at_risk: risk.at_risk,
    at_risk_reasons: risk.reasons, at_risk_since: risk.at_risk ? kr.at_risk_since ?? at : null, version: kr.version + 1, updated_at: at });
  recomputeObjective(s, o.id);
  return { checkIn: ci, becameAtRisk: became, expectedPct: risk.expected_pct };
}

/** `goals_seed._check_ins`: snapshot check-ins in date order per KR (KR owner = author). */
function seedCheckIns(s: GoalStore): void {
  const rows = [...(SNAP.check_ins ?? [])].sort((x, y) => x.date.localeCompare(y.date));
  for (const r of rows) {
    const k = s.krs.find((x) => x.id === krId(`${r.okr}:${r.key_result}`));
    if (!k) continue;
    k.owner_id = uId(r.by);
    checkInKr(s, k, { value: r.value, confidence: r.confidence, note: r.note, blocker: null, support_needed: null, next_action: null }, k.owner_id, checkedAt(r.date), SEED_DAY);
  }
}

/** `goals_seed._at_risk`: R-DEC-55 flags of every KR re-evaluated at the reference day (UC-04 → exactly one KR). */
function seedAtRisk(s: GoalStore): void {
  for (const k of s.krs) {
    const o = s.objectives.find((x) => x.id === k.objective_id)!;
    const last = s.krMeasurements.filter((m) => m.key_result_id === k.id).sort((x, y) => y.measured_at.localeCompare(x.measured_at))[0];
    const r = atRisk({ progress: k.progress_pct, previousProgress: last?.previous_progress_pct ?? null, confidence: k.confidence, periodKey: o.period_key, today: SEED_DAY });
    Object.assign(k, { at_risk: r.at_risk, at_risk_reasons: r.at_risk ? r.reasons : [], at_risk_since: r.at_risk ? k.last_checked_in_at ?? checkedAt(SEED_DAY) : null });
  }
  for (const o of s.objectives) recomputeObjective(s, o.id);
}

export type { MockClaims };

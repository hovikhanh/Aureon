/**
 * Pure helpers of the goals screens (SCR-41/58/59/60, T-626F..T-628F). The FE never computes a
 * KPI/KR number — bands, achievement, progress and at-risk come from the API; these helpers only
 * shape what is returned (filters, chart rows, error keys, week boundaries).
 */
import type { Api } from "@aureon/shared-types";
import { formatNumber, formatPct, type AppLocale } from "@/lib/format";
import { addDays, weekStart } from "@/lib/work-dates";

export type GoalTree = Api.GoalTreeOut;
export type KpiNode = Api.KpiNode;
export type ObjNode = Api.ObjNode;
export type KrNode = Api.KrNode;
export type SONode = Api.SONode;
export type Band = Api.KpiEvaluationBrief["band"];
export type Confidence = "HIGH" | "MEDIUM" | "LOW";
export const CONFIDENCES: readonly Confidence[] = ["HIGH", "MEDIUM", "LOW"];
export const BANDS: readonly Band[] = ["CRITICAL", "BELOW", "NEAR", "MEETS", "EXCEEDS"];

/** Band → Badge variant (06 §2 status colours). */
export const BAND_VARIANT: Record<Band, "danger" | "warning" | "success" | "primary"> = {
  CRITICAL: "danger", BELOW: "danger", NEAR: "warning", MEETS: "success", EXCEEDS: "primary",
};
export const isLowBand = (b: string | null | undefined) => b === "CRITICAL" || b === "BELOW";

/** "Chỉ mục at-risk / dưới ngưỡng" quick filter (SCR-41). */
export const kpiFlagged = (k: KpiNode): boolean => isLowBand(k.latest_evaluation?.band) || (k.children ?? []).some(kpiFlagged);
export const objFlagged = (o: ObjNode): boolean => (o.at_risk_kr_count ?? 0) > 0 || (o.key_results ?? []).some((k) => k.at_risk) || (o.children ?? []).some(objFlagged);

export function filterKpis(rows: readonly KpiNode[], onlyFlagged: boolean): KpiNode[] {
  return onlyFlagged ? rows.filter(kpiFlagged) : [...rows];
}
export function filterObjs(rows: readonly ObjNode[], onlyFlagged: boolean): ObjNode[] {
  return onlyFlagged ? rows.filter(objFlagged) : [...rows];
}
export function soVisible(so: SONode, onlyFlagged: boolean): boolean {
  return !onlyFlagged || (so.kpis ?? []).some(kpiFlagged) || (so.objectives ?? []).some(objFlagged) || (so.initiatives ?? []).some((i) => i.on_track === false);
}

/** Every KR node of the tree (for the team "chưa check-in tuần này" list). */
export function treeKrs(t: GoalTree | undefined): KrNode[] {
  if (!t) return [];
  const fromObj = (o: ObjNode): KrNode[] => [...(o.key_results ?? []), ...(o.children ?? []).flatMap(fromObj)];
  const sos = (t.strategies ?? []).flatMap((s) => s.strategic_objectives ?? []);
  return [...sos.flatMap((s) => (s.objectives ?? []).flatMap(fromObj)), ...(t.unaligned?.objectives ?? []).flatMap(fromObj)];
}

/** Monday..Sunday of the business week containing `today` (`from`/`to` of EP-PRF-05). */
export function weekRangeOf(today: string): { from: string; to: string } {
  const from = weekStart(today);
  return { from, to: addDays(from, 6) };
}
/** Was `iso` (UTC timestamp) on/after the Monday of this business week? */
export const checkedInThisWeek = (iso: string | null | undefined, today: string) => Boolean(iso && iso.slice(0, 10) >= weekStart(today));

export const daysAgo = (iso: string, today: string) =>
  Math.max(0, Math.round((Date.parse(`${today}T00:00:00Z`) - Date.parse(`${iso.slice(0, 10)}T00:00:00Z`)) / 86_400_000));

/** Chart rows (EP-KPI-10 evaluations): actual vs the target in force + NEAR/BELOW lines of that target. */
export interface ChartRow { period_key: string; actual: number; target: number; near: number; below: number; band: Band }
export function chartRows(evals: readonly Api.KpiEvaluationOut[], direction: string, thresholds: { NEAR: number; BELOW: number } = { NEAR: 90, BELOW: 70 }): ChartRow[] {
  // achievement bound → value: HIGHER = target·pct; LOWER = target / pct (achievement = target/actual)
  const at = (target: number, pct: number) => (direction === "LOWER_IS_BETTER" ? target / (pct / 100) : target * (pct / 100));
  const round = (n: number) => Math.round(n * 1000) / 1000;
  return [...evals].sort((a, b) => a.period_key.localeCompare(b.period_key)).map((e) => ({
    period_key: e.period_key, actual: e.actual_value, target: e.target, near: round(at(e.target, thresholds.NEAR)), below: round(at(e.target, thresholds.BELOW)), band: e.band,
  }));
}

/** Current period key of a KPI for "Ghi số đo" (mirror of `period_key_for`). */
export function periodKeyOf(periodType: string, day: string): string {
  const m = Number(day.slice(5, 7));
  if (periodType === "QUARTER") return `${day.slice(0, 4)}-Q${Math.floor((m - 1) / 3) + 1}`;
  if (periodType === "YEAR") return day.slice(0, 4);
  return day.slice(0, 7);
}

interface ErrorLike { code: string; details: Record<string, unknown> }
/** API error → `goals.errors.*` key. */
export function goalErrorKey(e: ErrorLike): string {
  if (e.code === "CONFLICT_STATE") {
    if (e.details.reason === "period_locked") return "periodLocked";
    if (e.details.reason === "objective_not_active") return "objectiveNotActive";
    return "conflict";
  }
  if (e.code === "BUSINESS_RULE_VIOLATION") {
    if (e.details.field === "period_key") return "periodMismatch";
    if (e.details.field === "valid_from") return "validFrom";
    if (e.details.reason === "kr_count") return "krCount";
    return "rule";
  }
  if (["FORBIDDEN_ROLE", "FORBIDDEN_SCOPE", "NOT_FOUND", "VALIDATION_ERROR", "BAD_REQUEST", "IDEMPOTENCY_CONFLICT"].includes(e.code)) return e.code;
  return "generic";
}

/** KPI/KR value with its free-text unit (`%` → 12,5%; others → "3,9 tỷ VND"). Formatting only. */
export function formatValue(value: number | null | undefined, unit: string | null | undefined, locale: AppLocale): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const u = (unit ?? "").trim();
  if (u === "%") return formatPct(value, locale);
  const n = formatNumber(value, locale, Number.isInteger(value) ? 0 : 2);
  return u ? (u === "x" ? `${n}x` : `${n} ${u}`) : n;
}

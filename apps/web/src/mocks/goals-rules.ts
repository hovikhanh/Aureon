/**
 * Pure goal maths mirrored from `execution/services/kpi_rules.py` (TC-EXE-004) + R-DEC-55 at-risk
 * rule (05 §2.6). Mock-side only: the API computes these and stores them (`kpi_evaluations`,
 * `key_results.at_risk`); the FE never computes KPI numbers.
 */
export type Band = "CRITICAL" | "BELOW" | "NEAR" | "MEETS" | "EXCEEDS";
export const DEFAULT_BANDS: Record<Band, number> = { CRITICAL: 0, BELOW: 70, NEAR: 90, MEETS: 100, EXCEEDS: 110 };
export const DEFAULT_CAP = 150;
/** R-DEC-54 defaults (`GOALS_*` ConfigService). */
export const KR_CHECKIN_MAX_AGE_DAYS = 7;
export const KR_BEHIND_RATIO = 0.7;
export const AT_RISK_MIN_DAYS = 21;

const r4 = (x: number) => Math.round(x * 10_000) / 10_000;
const ratio = (num: number, den: number, cap: number) => (den === 0 ? (num === 0 ? 100 : cap) : (num / den) * 100);

export function achievementPct(direction: string, actual: number, target: number, minimum: number | null = null, cap = DEFAULT_CAP): number {
  let raw: number;
  if (direction === "LOWER_IS_BETTER") raw = ratio(target, actual, cap);
  else if (direction === "BINARY") raw = actual >= target ? 100 : 0;
  else if (direction === "WITHIN_RANGE") {
    const low = minimum ?? target;
    raw = actual < low ? ratio(actual, low, cap) : actual > target ? ratio(target, actual, cap) : 100;
  } else raw = ratio(actual, target, cap);
  return r4(Math.min(Math.max(raw, 0), cap));
}

export function bandOf(achievement: number, thresholds: Record<string, number> = DEFAULT_BANDS): Band {
  const bounds = Object.entries(thresholds).sort((a, b) => a[1] - b[1]);
  let chosen = bounds[0]![0];
  for (const [name, low] of bounds) if (achievement >= low) chosen = name;
  return chosen as Band;
}

/** `gap_value` = how far from target in the good direction (≥ 0 when not reached). */
export function gapValue(direction: string, actual: number, target: number): number {
  return r4(direction === "LOWER_IS_BETTER" ? actual - target : target - actual);
}

export function krProgressPct(baseline: number, target: number, current: number | null): number {
  if (current === null) return 0;
  if (target === baseline) return current === target ? 100 : 0;
  return r4(Math.min(Math.max(((current - baseline) / (target - baseline)) * 100, 0), 100));
}

export function weightedAvg(pairs: readonly (readonly [number, number])[]): number {
  if (!pairs.length) return 0;
  const w = pairs.reduce((s, [, x]) => s + x, 0);
  return r4(w === 0 ? pairs.reduce((s, [v]) => s + v, 0) / pairs.length : pairs.reduce((s, [v, x]) => s + v * x, 0) / w);
}

export function periodKeyFor(periodType: string, day: string): string {
  const y = day.slice(0, 4);
  const m = Number(day.slice(5, 7));
  if (periodType === "QUARTER") return `${y}-Q${Math.floor((m - 1) / 3) + 1}`;
  if (periodType === "YEAR") return y;
  return day.slice(0, 7);
}

/** `[start, end)` of `YYYY-MM` / `YYYY-Qn` / `YYYY`; `null` when malformed. */
export function periodBounds(key: string): [string, string] | null {
  const pad = (n: number) => String(n).padStart(2, "0");
  let m = /^(\d{4})$/.exec(key);
  if (m) return [`${m[1]}-01-01`, `${Number(m[1]) + 1}-01-01`];
  m = /^(\d{4})-Q([1-4])$/.exec(key);
  if (m) {
    const y = Number(m[1]);
    const q = Number(m[2]);
    return [`${y}-${pad(3 * q - 2)}-01`, q === 4 ? `${y + 1}-01-01` : `${y}-${pad(3 * q + 1)}-01`];
  }
  m = /^(\d{4})-(0[1-9]|1[0-2])$/.exec(key);
  if (m) {
    const y = Number(m[1]);
    const mo = Number(m[2]);
    return [`${y}-${pad(mo)}-01`, mo === 12 ? `${y + 1}-01-01` : `${y}-${pad(mo + 1)}-01`];
  }
  return null;
}

/** Does `key` have the shape of `periodType` (EP-KPI-07 `period_key` lệch `period_type` → 422)? */
export function periodMatchesType(key: string, periodType: string): boolean {
  if (periodType === "QUARTER") return /^\d{4}-Q[1-4]$/.test(key);
  if (periodType === "YEAR") return /^\d{4}$/.test(key);
  return /^\d{4}-(0[1-9]|1[0-2])$/.test(key);
}

export const daysBetween = (a: string, b: string) => Math.round((Date.parse(`${b.slice(0, 10)}T00:00:00Z`) - Date.parse(`${a.slice(0, 10)}T00:00:00Z`)) / 86_400_000);

export type AtRiskReason = "declining" | "low_confidence" | "behind_plan";
/** R-DEC-55: reasons ∪ and ≥ 21 days left in the Objective period. */
export function atRisk(o: { progress: number; previousProgress: number | null; confidence: string | null; periodKey: string; today: string }): { at_risk: boolean; reasons: AtRiskReason[] } {
  const reasons: AtRiskReason[] = [];
  if (o.previousProgress !== null && o.progress < o.previousProgress) reasons.push("declining");
  if (o.confidence === "LOW") reasons.push("low_confidence");
  const b = periodBounds(o.periodKey);
  if (!b) return { at_risk: false, reasons };
  const span = daysBetween(b[0], b[1]);
  const elapsed = Math.min(1, Math.max(0, daysBetween(b[0], o.today) / span));
  if (o.progress < KR_BEHIND_RATIO * elapsed * 100) reasons.push("behind_plan");
  return { at_risk: reasons.length > 0 && daysBetween(o.today, b[1]) >= AT_RISK_MIN_DAYS, reasons };
}

/** SEI rule (DEC-226) behind `on_track`: progress ≥ 0,9 × linear plan. */
export function onTrack(progress: number, start: string, end: string, today: string): boolean {
  const span = daysBetween(start, end);
  const plan = span <= 0 ? 100 : Math.min(100, Math.max(0, (daysBetween(start, today) / span) * 100));
  return progress >= 0.9 * plan;
}

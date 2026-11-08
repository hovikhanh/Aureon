/**
 * Pure display helpers for the MVP acceptance page (M3.5, EP-RPT-08) — no React, Vitest-tested.
 * `gateTone` maps a gate status to a semantic badge tone; `formatValue` renders value + unit.
 */
import { formatNumber, formatPct, type AppLocale } from "@/lib/format";

export type GateStatus = "pass" | "warning" | "fail" | "no_data";
export type Tone = "success" | "warning" | "danger" | "muted";

const TONE: Record<GateStatus, Tone> = {
  pass: "success",
  warning: "warning",
  fail: "danger",
  no_data: "muted",
};

export function gateTone(status: string): Tone {
  return TONE[status as GateStatus] ?? "muted";
}

/** value + unit (P04): pct → "80,0%", days_per_week → "4 ngày/tuần", count → integer; null → "—". */
export function formatValue(value: number | null | undefined, unit: string, locale: AppLocale, daysPerWeek: string): string {
  if (value == null || Number.isNaN(value)) return "—";
  if (unit === "pct") return formatPct(value, locale);
  if (unit === "days_per_week") return `${formatNumber(value, locale, 1)} ${daysPerWeek}`;
  return formatNumber(Math.round(value), locale, 0);
}

/** Overall MVP gate: pass only when every gate passes; fail if any fails; else warning/no_data. */
export function overallStatus(statuses: string[]): GateStatus {
  if (statuses.length === 0) return "no_data";
  if (statuses.some((s) => s === "fail")) return "fail";
  if (statuses.some((s) => s === "warning")) return "warning";
  if (statuses.every((s) => s === "pass")) return "pass";
  return "no_data";
}

/** What a gate is measured from, in i18n terms: `source_ref` is an API path or a metric code, never shown raw. */
export function gateSourceKey(sourceRef: string): string | null {
  if (sourceRef.startsWith("METRIC-")) return `metric.${sourceRef}`;
  return { "/ai/briefings": "acceptance.sourceRef.briefings", "/idp/incidents": "acceptance.sourceRef.incidents" }[sourceRef] ?? null;
}

/**
 * Pure display helpers for the MVP acceptance page (M3.5, EP-RPT-08) — no React, Vitest-tested.
 * `gateTone` maps a gate status to a semantic badge tone; `formatValue` renders value + unit.
 */
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

/** value + unit: pct → "80.0%", days_per_week → "4.0 d/wk", count → integer; null → "—". */
export function formatValue(value: number | null | undefined, unit: string): string {
  if (value == null || Number.isNaN(value)) return "—";
  if (unit === "pct") return `${value.toFixed(1)}%`;
  if (unit === "days_per_week") return `${value.toFixed(1)} d/wk`;
  return String(Math.round(value));
}

/** Overall MVP gate: pass only when every gate passes; fail if any fails; else warning/no_data. */
export function overallStatus(statuses: string[]): GateStatus {
  if (statuses.length === 0) return "no_data";
  if (statuses.some((s) => s === "fail")) return "fail";
  if (statuses.some((s) => s === "warning")) return "warning";
  if (statuses.every((s) => s === "pass")) return "pass";
  return "no_data";
}

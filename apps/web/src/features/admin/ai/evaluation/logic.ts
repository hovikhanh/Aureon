/**
 * Pure display helpers for the AI Evaluation view (M3.4) — no React, unit-tested with Vitest.
 * `scoreBand` maps a percentage to a semantic colour band; `fmtPct` formats a 0–100 number.
 */
export type Band = "good" | "warn" | "bad";

/** ≥ 90 good · 70–<90 warn · < 70 bad (mirrors the dashboard health bands). */
export function scoreBand(pct: number): Band {
  if (pct >= 90) return "good";
  if (pct >= 70) return "warn";
  return "bad";
}

export function fmtPct(pct: number | null | undefined): string {
  if (pct == null || Number.isNaN(pct)) return "—";
  return `${pct.toFixed(1)}%`;
}

/** Latest-first by `finished_at` (ISO8601); runs without a finish time sort last. */
export function sortRunsByFinished<T extends { finished_at?: string | null }>(runs: T[]): T[] {
  return [...runs].sort((a, b) => (b.finished_at ?? "").localeCompare(a.finished_at ?? ""));
}

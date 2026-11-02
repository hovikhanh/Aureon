/** Pure helpers for the SCR-12 metric-detail panel (unit-tested in metric-detail.test.ts). */
import type { MetricDetail, TrendPoint } from "./types";

export interface ChartPoint {
  period_key: string;
  value: number | null;
}

/** Trend oldest→newest for the line chart; EP-12 returns newest-first per 10 §5. */
export function chartSeries(trend: TrendPoint[]): ChartPoint[] {
  return [...trend].reverse().map((p) => ({ period_key: p.period_key, value: p.value }));
}

/** True when a line chart is worth drawing (≥ 2 non-null points). */
export function hasTrend(trend: TrendPoint[]): boolean {
  return trend.filter((p) => p.value !== null).length >= 2;
}

/**
 * Threshold reference lines; `direction` sets which side is "good":
 * `down` → lower is better (warn/crit are ceilings), `up` → higher is better (floors).
 */
export function thresholdLines(d: Pick<MetricDetail, "thresholds" | "direction">): {
  warning: number;
  critical: number;
  direction: "up" | "down";
} {
  return { warning: d.thresholds.warning, critical: d.thresholds.critical, direction: d.direction };
}

/** Share of records behind the metric that carry source lineage (breakdown record_count sum). */
export function totalRecords(d: Pick<MetricDetail, "breakdown">): number {
  return d.breakdown.reduce((n, r) => n + (r.record_count || 0), 0);
}

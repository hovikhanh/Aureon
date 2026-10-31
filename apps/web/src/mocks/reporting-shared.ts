/** Shared metric projection for the dashboard + reporting mocks (T-604, T-707F). */
import { SNAPSHOT } from "./fixtures";

export { SNAPSHOT };
export const COMPUTED_AT = `${SNAPSHOT.reference_date}T01:00:00Z`;

/** MetricValueOut wire shape (10 §4.2 + M2.1 group/is_stale/max_age_hours, R-DEC-82/86). */
export function metricOut(m: (typeof SNAPSHOT.metrics)[number]) {
  return {
    metric_code: m.code, pillar: m.pillar, group: groupOf(m.code), value: m.value, unit: m.unit,
    currency: m.unit === "VND" ? "VND" : null, status: m.status, status_reason: null,
    period_key: m.period_key, computed_at: COMPUTED_AT, freshness: "fresh" as const,
    is_stale: false, max_age_hours: 24, data_quality_pct: null,
    lineage_url: `/dashboard/metrics/${m.code}/lineage`,
  };
}

// code → nhóm v3 (song song pillar); null = p1_frozen (RSK nghiệp vụ, PRD) — không vào group view.
const GROUP_OF: Record<string, string | null> = {
  "METRIC-FIN-01": "FIN", "METRIC-FIN-02": "FIN", "METRIC-FIN-03": "FIN", "METRIC-FIN-04": "FIN",
  "METRIC-FIN-05": "FIN", "METRIC-FIN-06": "FIN", "METRIC-FIN-07": "FIN",
  "METRIC-CUS-01": "CUS", "METRIC-CUS-02": "CUS", "METRIC-CUS-03": "CUS", "METRIC-CUS-04": "CUS",
  "METRIC-CUS-05": "CUS", "METRIC-CUS-06": "CUS",
  "METRIC-OPS-01": "OPS", "METRIC-OPS-02": "OPS", "METRIC-OPS-03": "OPS", "METRIC-HR-03": "OPS",
  "METRIC-HR-01": "PPL", "METRIC-HR-02": "PPL", "METRIC-HR-04": "PPL",
  "METRIC-STR-01": "STR", "METRIC-STR-02": "STR",
  "METRIC-DQ-01": "DQ", "METRIC-DQ-02": "DQ",
};

export function groupOf(code: string): string | null {
  return GROUP_OF[code] ?? null;
}

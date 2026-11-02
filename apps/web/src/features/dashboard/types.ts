/** 10 §4.2 MetricValueOut / §5 domain dashboard contract (subset used by SCR-02 cards). */
export type PillarCode = "F" | "O" | "C" | "U" | "S";
export type PillarStatus = "ok" | "warning" | "critical" | "no_data";
export type CardStatus = PillarStatus | "unavailable";

export interface MetricValue {
  metric_code: string;
  value: number | null;
  unit: string;
  status: PillarStatus;
  period_key?: string;
  computed_at: string;
  freshness: "fresh" | "stale";
  lineage_url: string;
  currency?: string | null;
}

export interface DomainDashboard {
  pillar: PillarCode;
  status: PillarStatus;
  period: { key: string; type: string; start_date: string; end_date: string };
  summary: Record<string, number | string | null>;
  metrics: MetricValue[];
  open_alerts: number | null;
}

export interface AlertOut {
  id: string;
  alert_code: string;
  metric_code: string;
  pillar: PillarCode | null;
  severity: "warning" | "critical";
  status: "open" | "acknowledged" | "resolved" | "dismissed";
  value: number | null;
  threshold: number;
  period_key: string;
  raised_at: string;
  message_key: string;
  message_params: Record<string, unknown>;
}

/** 10 §5 EP-12 MetricDetail — full drill-down contract (SCR-02..06, 12). */
export interface TrendPoint {
  period_key: string;
  value: number | null;
}

export interface BreakdownRow {
  key: string;
  label: string;
  value: number | null;
  record_count: number;
}

export interface MetricDetail extends MetricValue {
  name: string;
  formula_display: string;
  direction: "up" | "down";
  status_reason?: string | null;
  data_quality_pct?: number | null;
  is_stale?: boolean;
  max_age_hours?: number;
  thresholds: { warning: number; critical: number };
  trend: TrendPoint[];
  breakdown: BreakdownRow[];
  related_alerts: AlertOut[];
  data_source: { module: string; entities: string[] };
}

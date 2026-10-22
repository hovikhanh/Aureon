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

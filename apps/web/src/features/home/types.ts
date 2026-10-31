/** SCR-40 Reporting v3 client types (EP-RPT-01..05, 10 §7.2.6). Mirror the BE schemas. */

export interface MetricValue {
  metric_code: string;
  pillar: string | null;
  group: string | null;
  value: number | null;
  unit: string;
  currency: string | null;
  status: "ok" | "warning" | "critical" | "no_data";
  period_key: string;
  computed_at: string;
  freshness: "fresh" | "stale";
  is_stale: boolean;
  max_age_hours: number;
  lineage_url: string;
}

export interface AlertBrief {
  id: string;
  alert_code: string;
  metric_code: string;
  severity: "warning" | "critical";
  value: number | null;
}

export interface AiActionBrief {
  id: string;
  action_name: string;
  status: string;
  executed_at: string | null;
}

export interface Counted<T> {
  count: number;
  items: T[];
}

export interface ExecutiveDashboard {
  summary_line: string;
  tiles: MetricValue[];
  sei: MetricValue | null;
  decisions_waiting: Counted<unknown>;
  open_risks: Counted<AlertBrief>;
  ai_done: Counted<AiActionBrief>;
  generated_at: string;
}

export interface DepartmentDashboard {
  department_id: string | null;
  kpis: MetricValue[];
  okrs: { at_risk_count: number; total: number };
  workload: { overloaded_count: number; heatmap_ref: string };
  late_projects: number;
  due_tasks: { overdue: number; today: number; this_week: number };
  generated_at: string;
}

export interface EmployeeDashboard {
  my_tasks: { overdue: number; today: number; this_week: number };
  my_goals: { kpis: number; krs: number };
  pending_checkins: { target_type: string; target_id: string; label: string; period_key: string }[];
  workload_week_pct: number | null;
  generated_at: string;
}

export interface ExecutiveTiles {
  tiles: string[];
  version: number;
}

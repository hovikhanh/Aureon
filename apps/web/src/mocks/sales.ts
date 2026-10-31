/**
 * M2.2 Sales pipeline mock (T-715F) — EP-75 (pipeline), EP-70 (dashboard). Same wire format as
 * the BE SalesService (schemas/__init__.py): `PipelineOut` / `SalesDashboardOut`, deal stages in
 * the canonical order lead→qualified→proposal→negotiation→closed_won→closed_lost. win_rate_pct
 * comes from SNAPSHOT METRIC-CUS-02 (100.0).
 *
 * Permission (mirror BE 10 §7.2.7): both pipeline + dashboard are AGGREGATE `sales:query` — open
 * to every DIR/CEO regardless of pillar (R-DEC-89). Pillar scoping (F vs C) applies only to the
 * detailed `:read` lists (EP /sales/deals), not to these aggregates; the mock must not be stricter
 * than the real backend. The router `permission` field enforces `sales:query` (default-deny 403).
 */
import { ok } from "./http";
import type { Route } from "./router";
import { SNAPSHOT } from "./reporting-shared";

const CURRENCY = "VND";
const PERIOD_Q3 = { key: "2026-Q3", type: "quarter", start_date: "2026-07-01", end_date: "2026-09-30" };

function cusValue(code: string): number | null {
  return SNAPSHOT.metrics.find((m) => m.code === code)?.value ?? null;
}

// Pipeline by stage (canonical order). weighted_value ≈ value × stage win probability.
const STAGE_DATA: { stage: string; count: number; value: number; weighted_value: number; avg_days_in_stage: number | null }[] = [
  { stage: "lead", count: 24, value: 18_000_000_000, weighted_value: 1_800_000_000, avg_days_in_stage: 9.5 },
  { stage: "qualified", count: 15, value: 22_000_000_000, weighted_value: 6_600_000_000, avg_days_in_stage: 12.0 },
  { stage: "proposal", count: 9, value: 16_500_000_000, weighted_value: 8_250_000_000, avg_days_in_stage: 14.3 },
  { stage: "negotiation", count: 5, value: 11_000_000_000, weighted_value: 8_800_000_000, avg_days_in_stage: 18.7 },
  { stage: "closed_won", count: 7, value: 13_500_000_000, weighted_value: 13_500_000_000, avg_days_in_stage: null },
  { stage: "closed_lost", count: 3, value: 4_200_000_000, weighted_value: 0, avg_days_in_stage: null },
];

const OPEN_STAGES = ["lead", "qualified", "proposal", "negotiation"];

function pipeline(): Response {
  const openValue = STAGE_DATA.filter((s) => OPEN_STAGES.includes(s.stage)).reduce((a, s) => a + s.value, 0);
  const quota = 60_000_000_000;
  return ok({
    period: PERIOD_Q3,
    stages: STAGE_DATA,
    coverage_ratio: Math.round((openValue / quota) * 100) / 100,
    currency: CURRENCY,
  });
}

function dashboard(): Response {
  const open = STAGE_DATA.filter((s) => OPEN_STAGES.includes(s.stage));
  const won = STAGE_DATA.find((s) => s.stage === "closed_won")!;
  const lost = STAGE_DATA.find((s) => s.stage === "closed_lost")!;
  const pipelineValue = open.reduce((a, s) => a + s.value, 0);
  const weighted = open.reduce((a, s) => a + s.weighted_value, 0);
  const dealsOpen = open.reduce((a, s) => a + s.count, 0);
  const closedRevenue = won.value;
  return ok({
    pillar: "C",
    status: "ok",
    period: PERIOD_Q3,
    summary: {
      pipeline_value: pipelineValue,
      weighted_pipeline: weighted,
      deals_open: dealsOpen,
      deals_won: won.count,
      deals_lost: lost.count,
      win_rate_pct: cusValue("METRIC-CUS-02"), // 100.0
      avg_deal_value: Math.round(closedRevenue / won.count),
      closed_revenue: closedRevenue,
      quota_attainment_pct: cusValue("METRIC-CUS-03"), // 103.7
      avg_sales_cycle_days: cusValue("METRIC-CUS-06"), // 60.0
      pipeline_coverage: cusValue("METRIC-CUS-01"), // 2.7
      currency: CURRENCY,
    },
    metrics: [],
    pipeline_trend: [
      { period_key: "2026-07", pipeline_value: 58_000_000_000, weighted_pipeline: 22_100_000_000 },
      { period_key: "2026-08", pipeline_value: 64_500_000_000, weighted_pipeline: 24_000_000_000 },
      { period_key: "2026-09", pipeline_value: pipelineValue, weighted_pipeline: weighted },
    ],
    win_rate_trend: [
      { period_key: "2026-07", won: 5, lost: 2, win_rate_pct: 71.4 },
      { period_key: "2026-08", won: 6, lost: 2, win_rate_pct: 75.0 },
      { period_key: "2026-09", won: won.count, lost: lost.count, win_rate_pct: cusValue("METRIC-CUS-02") },
    ],
    open_alerts: 0,
  });
}

// Perm mirrors BE 10 §7.2.7: pipeline + dashboard aggregate = sales:query (open to all DIR).
export const SALES_ROUTES: readonly Route[] = [
  { method: "GET", pattern: "/sales/pipeline", permission: "sales:query", handler: pipeline },
  { method: "GET", pattern: "/sales/dashboard", permission: "sales:query", handler: dashboard },
];

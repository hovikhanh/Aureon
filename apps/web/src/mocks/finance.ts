/**
 * M2.2 Finance Lite mock (T-715F) — EP-60 (dashboard), EP-64 (budget status), EP-69 (what-if
 * runway). Same wire format as the BE FinanceService (schemas/__init__.py): `{data, meta?}`
 * envelope, same field names/types, `BudgetStatus = "ok"|"warning"|"critical"`,
 * `RunwayWhatIfOut` carries `sources[]` (SourceRef). Numbers come from `SNAPSHOT.metrics`
 * (METRIC-FIN-01..06) where possible; the rest are deterministic constants consistent with the
 * seed (công ty ABC, ~300 tỷ/năm, Q3/2026).
 *
 * Role gate (mirror BE `require_permission("finance:read"|"finance:query")` + scope): CEO always;
 * DIR only when claims `scope_pillars` include "F" (role CFO) — otherwise 403 FORBIDDEN_ROLE.
 * This mirrors `store.ts` `seesFullFinance` (CEO | DIR∈{F,S}); here F is required for the full view.
 */
import { ok, fail } from "./http";
import type { MockRequest, Route } from "./router";
import { SNAPSHOT, COMPUTED_AT } from "./reporting-shared";
import { mockId } from "./fixtures";

const CURRENCY = "VND";
const PERIOD_Q3 = { key: "2026-Q3", type: "quarter", start_date: "2026-07-01", end_date: "2026-09-30" };

/** Full Finance view = CEO, or DIR whose pillar scope includes "F" (role CFO). */
function seesFinance(claims: MockRequest["claims"]): boolean {
  if (claims.role === "CEO") return true;
  return claims.role === "DIR" && claims.scope_pillars.includes("F");
}

function guard(claims: MockRequest["claims"]): Response | null {
  if (!seesFinance(claims)) return fail(403, "FORBIDDEN_ROLE", "finance view is CEO/CFO only", { pillar: "F" });
  return null;
}

/** Finance metric value by code from the snapshot (METRIC-FIN-01..07). */
function finValue(code: string): number | null {
  return SNAPSHOT.metrics.find((m) => m.code === code)?.value ?? null;
}

/** Last 6 months of revenue/expense (~23–25 tỷ/tháng), deterministic, consistent with ~300 tỷ/năm. */
const REVENUE_TREND: { period_key: string; revenue: number; expense: number }[] = [
  { period_key: "2026-04", revenue: 23_100_000_000, expense: 21_800_000_000 },
  { period_key: "2026-05", revenue: 24_200_000_000, expense: 22_400_000_000 },
  { period_key: "2026-06", revenue: 23_700_000_000, expense: 22_900_000_000 },
  { period_key: "2026-07", revenue: 25_100_000_000, expense: 23_300_000_000 },
  { period_key: "2026-08", revenue: 24_600_000_000, expense: 23_900_000_000 },
  { period_key: "2026-09", revenue: 24_900_000_000, expense: 24_100_000_000 },
];

// runway_months ~ 5–8 (seed METRIC-FIN-03 = 5.3, critical)
const RUNWAY_TREND: { period_key: string; runway_months: number | null }[] = [
  { period_key: "2026-04", runway_months: 7.8 },
  { period_key: "2026-05", runway_months: 7.1 },
  { period_key: "2026-06", runway_months: 6.5 },
  { period_key: "2026-07", runway_months: 6.0 },
  { period_key: "2026-08", runway_months: 5.6 },
  { period_key: "2026-09", runway_months: finValue("METRIC-FIN-03") ?? 5.3 },
];

const CLOSING_BALANCE = 128_000_000_000; // ~128 tỷ tiền mặt
const AVG_REVENUE_3M = 24_866_666_667; // trung bình 3 tháng gần nhất (T7–T9)
const AVG_EXPENSE_3M = 23_766_666_667;
const NET_BURN = AVG_EXPENSE_3M - AVG_REVENUE_3M; // > 0 khi đốt tiền; ở đây nhỏ (gần hòa vốn)

function financeMetricOut(code: string) {
  const m = SNAPSHOT.metrics.find((x) => x.code === code)!;
  return {
    metric_code: m.code, value: m.value, unit: m.unit, status: m.status,
    computed_at: COMPUTED_AT, freshness: "fresh" as const, data_quality_pct: null,
    lineage_url: `/dashboard/metrics/${m.code}/lineage`,
  };
}

function dashboard(req: MockRequest): Response {
  const blocked = guard(req.claims);
  if (blocked) return blocked;
  const latest = REVENUE_TREND.at(-1)!;
  return ok({
    pillar: "F",
    status: "warning",
    period: PERIOD_Q3,
    summary: {
      total_revenue: 73_700_000_000, // tổng doanh thu Q3 (T7–T9)
      total_expense: 71_300_000_000,
      net_profit: 2_400_000_000,
      gross_margin_pct: finValue("METRIC-FIN-02"), // 18.4
      gross_burn: latest.expense,
      net_burn: NET_BURN,
      runway_months: finValue("METRIC-FIN-03"), // 5.3
      revenue_growth_pct: finValue("METRIC-FIN-05"), // 7.9
      budget_utilization_pct: finValue("METRIC-FIN-01"), // 86.4
      overdue_ar: 4_200_000_000,
      dso_days: finValue("METRIC-FIN-04"), // 54.4
      currency: CURRENCY,
    },
    metrics: ["METRIC-FIN-01", "METRIC-FIN-02", "METRIC-FIN-03", "METRIC-FIN-04", "METRIC-FIN-05", "METRIC-FIN-06"].map(financeMetricOut),
    revenue_trend: REVENUE_TREND,
    runway_trend: RUNWAY_TREND,
    open_alerts: SNAPSHOT.metrics.filter((m) => m.pillar === "F" && (m.status === "warning" || m.status === "critical")).length,
  });
}

// Per-department Q3/2026 budget allocation vs spend; status = BudgetStatus ("ok"|"warning"|"critical").
const BUDGETS: { dept: string; allocated: number; spent: number; status: "ok" | "warning" | "critical" }[] = [
  { dept: "SALES", allocated: 18_000_000_000, spent: 15_600_000_000, status: "ok" },
  { dept: "OPS", allocated: 12_000_000_000, spent: 11_400_000_000, status: "warning" },
  { dept: "HR", allocated: 9_000_000_000, spent: 7_200_000_000, status: "ok" },
  { dept: "MKT", allocated: 6_000_000_000, spent: 6_300_000_000, status: "critical" },
  { dept: "IT", allocated: 5_000_000_000, spent: 3_900_000_000, status: "ok" },
];

function budgetStatus(req: MockRequest): Response {
  const blocked = guard(req.claims);
  if (blocked) return blocked;
  const rows = BUDGETS.map((b) => ({
    budget_id: mockId("budget", `${b.dept}:2026-Q3`),
    department_id: mockId("department", b.dept),
    period: "2026-Q3",
    allocated_amount: b.allocated,
    spent_amount: b.spent,
    budget_utilization_pct: Math.round((b.spent / b.allocated) * 1000) / 10,
    currency: CURRENCY,
    status: b.status,
  }));
  return ok(rows);
}

function num(q: URLSearchParams, name: string): number {
  const raw = q.get(name);
  if (raw === null || raw === "") return 0;
  const n = Number(raw);
  return Number.isFinite(n) ? n : 0;
}

/** EP-69 what-if: recompute runway from the 3-month averages + the requested deltas. */
function whatIfRunway(req: MockRequest): Response {
  const blocked = guard(req.claims);
  if (blocked) return blocked;
  const revenueChangePct = num(req.query, "revenue_change_pct");
  const expenseChangePct = num(req.query, "expense_change_pct");
  const extraMonthlyCost = Math.trunc(num(req.query, "extra_monthly_cost"));

  const adjRevenue = AVG_REVENUE_3M * (1 + revenueChangePct / 100);
  const adjExpense = AVG_EXPENSE_3M * (1 + expenseChangePct / 100) + extraMonthlyCost;
  const netBurn = Math.round(adjExpense - adjRevenue);
  const runwayNoNewRevenue = CLOSING_BALANCE / (AVG_EXPENSE_3M + extraMonthlyCost);
  const runway = netBurn > 0 ? CLOSING_BALANCE / netBurn : null; // null = không đốt tiền ròng

  const round1 = (x: number) => Math.round(x * 10) / 10;
  return ok({
    as_of: SNAPSHOT.reference_date,
    runway_months_no_new_revenue: round1(runwayNoNewRevenue),
    runway_months: runway === null ? null : round1(runway),
    closing_balance: CLOSING_BALANCE,
    avg_expense_3m: AVG_EXPENSE_3M,
    avg_revenue_3m: AVG_REVENUE_3M,
    net_burn: netBurn,
    revenue_change_pct: revenueChangePct,
    expense_change_pct: expenseChangePct,
    extra_monthly_cost: extraMonthlyCost,
    currency: CURRENCY,
    status_reason: runway === null ? "net_positive_cash_flow" : null,
    sources: [
      { type: "record", id: "cash:2026-09", label: "Số dư tiền mặt T9/2026", period_key: "2026-09", value: CLOSING_BALANCE, lineage_url: "/finance/cash-positions" },
      { type: "metric_value", id: "METRIC-FIN-03", label: "Runway (tháng)", period_key: "2026-09", value: finValue("METRIC-FIN-03"), lineage_url: "/dashboard/metrics/METRIC-FIN-03/lineage" },
    ],
  });
}

// Perm mirrors BE: dashboard/status = finance:read; what-if = finance:query (CLAUDE §5.2, 10 §4.6).
export const FINANCE_ROUTES: readonly Route[] = [
  { method: "GET", pattern: "/finance/dashboard", permission: "finance:read", handler: dashboard },
  { method: "GET", pattern: "/finance/budgets/status", permission: "finance:read", handler: budgetStatus },
  { method: "GET", pattern: "/finance/what-if/runway", permission: "finance:query", handler: whatIfRunway },
];

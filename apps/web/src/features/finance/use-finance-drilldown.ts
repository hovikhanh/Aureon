"use client";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { qk } from "@/lib/query-keys";
import type { MetricValue, PillarStatus } from "@/features/dashboard/types";
import { CARDS, monthOf, trendOf, type CardDef, type Trend } from "./drilldown";

interface FinanceDashboard {
  status: PillarStatus;
  period: { key: string; type: string; start_date: string; end_date: string };
  summary: {
    total_revenue: number; total_expense: number; net_burn: number;
    runway_months: number | null; budget_utilization_pct: number | null; currency: string;
  };
  metrics: MetricValue[];
  revenue_trend: { period_key: string; revenue: number; expense: number }[];
  runway_trend: { period_key: string; runway_months: number | null }[];
}

interface CashPosition { period: string; closing_balance: number; opening_balance: number | null }

export interface CardView extends CardDef {
  value: number | null;
  series: number[];
  trend: Trend;
  status: MetricValue["status"] | null;
}

export function useFinanceDrilldown(period: string) {
  const dash = useQuery({
    queryKey: qk.pillar("finance", period),
    queryFn: ({ signal }) => api.get<FinanceDashboard>("/finance/dashboard", { period }, signal),
  });
  const cash = useQuery({
    queryKey: ["finance", "cash-positions", "last14"],
    queryFn: ({ signal }) =>
      api.get<CashPosition[]>("/finance/cash-positions", { limit: 14, sort_by: "period", order: "desc" }, signal),
    staleTime: 300_000,
  });

  const d = dash.data;
  const month = d ? monthOf(d.period) : null;
  const cashAsc = [...(cash.data ?? [])].filter((c) => !month || c.period <= month).reverse();
  const statusOf = (code: string) => d?.metrics.find((m) => m.metric_code === code)?.status ?? null;

  const raw: Record<CardDef["key"], { value: number | null; series: number[] }> = {
    revenue: { value: d?.summary.total_revenue ?? null, series: d?.revenue_trend.map((p) => p.revenue) ?? [] },
    expense: { value: d?.summary.total_expense ?? null, series: d?.revenue_trend.map((p) => p.expense) ?? [] },
    budget: { value: d?.summary.budget_utilization_pct ?? null, series: [] },
    runway: {
      value: d?.summary.runway_months ?? null,
      series: (d?.runway_trend ?? []).map((p) => p.runway_months).filter((v): v is number => v !== null),
    },
    cash: { value: cashAsc.at(-1)?.closing_balance ?? null, series: cashAsc.map((c) => c.closing_balance) },
    burn: { value: d?.summary.net_burn ?? null, series: [] },
  };

  const cards: CardView[] = CARDS.map((c) => ({
    ...c,
    ...raw[c.key],
    trend: trendOf(raw[c.key].series),
    status: statusOf(c.metric),
  }));

  return {
    loading: dash.isLoading,
    error: dash.isError,
    refetch: () => void dash.refetch(),
    status: d?.status ?? null,
    periodKey: d?.period.key ?? period,
    month,
    cards,
  };
}

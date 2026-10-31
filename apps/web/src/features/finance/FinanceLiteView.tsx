"use client";
import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiRequest } from "@/lib/api-client";
import { formatMoney, formatMoneyShort, formatNumber, formatPct, type AppLocale } from "@/lib/format";
import { qk } from "@/lib/query-keys";
import { cn } from "@/lib/utils";

interface FinanceSummary {
  total_revenue: number;
  total_expense: number;
  net_profit: number;
  runway_months: number | null;
  budget_utilization_pct: number | null;
  currency: string;
}
interface FinanceDashboardOut {
  status: "ok" | "warning" | "critical" | "no_data";
  summary: FinanceSummary;
}
interface BudgetStatusOut {
  budget_id: string;
  department_id: string;
  period: string;
  allocated_amount: number;
  spent_amount: number;
  budget_utilization_pct: number;
  currency: string;
  status: "ok" | "warning" | "critical";
}
interface RunwayWhatIfOut {
  runway_months: number | null;
  runway_months_no_new_revenue: number | null;
  closing_balance: number | null;
  net_burn: number | null;
  currency: string;
}

const SUMMARY_KEYS = ["total_revenue", "net_profit", "runway_months", "budget_utilization_pct"] as const;
type SummaryKey = (typeof SUMMARY_KEYS)[number];

const STATUS_CLASS: Record<BudgetStatusOut["status"], string> = {
  ok: "text-success",
  warning: "text-warning",
  critical: "text-danger",
};

/** M2.2 Finance Lite overview (T-715F, SCR-46): budget utilization, cash balance, runway. */
export function FinanceLiteView() {
  const t = useTranslations();
  const locale = useLocale() as AppLocale;

  const dash = useQuery({
    queryKey: qk.financeDashboard(),
    queryFn: ({ signal }) => apiRequest<FinanceDashboardOut>("/finance/dashboard", { signal }),
  });
  const budgets = useQuery({
    queryKey: qk.financeBudgetStatus(),
    queryFn: ({ signal }) => apiRequest<BudgetStatusOut[]>("/finance/budgets/status", { signal }),
  });
  const whatIfParams = { revenue_change_pct: 0, expense_change_pct: 0, extra_monthly_cost: 0 };
  const runway = useQuery({
    queryKey: qk.financeRunwayWhatIf(whatIfParams),
    queryFn: ({ signal }) => apiRequest<RunwayWhatIfOut>("/finance/what-if/runway", { query: whatIfParams, signal }),
  });

  const summary = dash.data?.data.summary;
  const budgetRows = budgets.data?.data ?? [];
  const runwayData = runway.data?.data;

  function summaryValue(key: SummaryKey): string {
    if (!summary) return "—";
    switch (key) {
      case "total_revenue":
        return formatMoneyShort(summary.total_revenue, locale);
      case "net_profit":
        return formatMoneyShort(summary.net_profit, locale);
      case "runway_months":
        return summary.runway_months === null ? "—" : t("financeLite.monthsValue", { value: formatNumber(summary.runway_months, locale, 1) });
      case "budget_utilization_pct":
        return summary.budget_utilization_pct === null ? "—" : formatPct(summary.budget_utilization_pct, locale);
    }
  }

  return (
    <div className="mx-auto flex max-w-[1400px] flex-col gap-6" data-testid="finance-lite">
      <h1 className="text-2xl font-semibold">{t("financeLite.title")}</h1>

      {/* Summary cards */}
      <section aria-label={t("financeLite.summaryTitle")}>
        {dash.isPending && <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">{SUMMARY_KEYS.map((k) => <div key={k} className="h-24 animate-pulse rounded-lg bg-muted" />)}</div>}
        {dash.isError && <p role="alert" className="text-danger">{t("errors.generic")}</p>}
        {dash.isSuccess && !summary && <p className="text-muted-foreground">{t("financeLite.empty")}</p>}
        {dash.isSuccess && summary && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {SUMMARY_KEYS.map((key) => (
              <Card key={key} data-testid={`fin-summary-${key}`}>
                <CardHeader>
                  <CardTitle className="text-sm font-medium text-muted-foreground">{t(`financeLite.summary.${key}`)}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-2xl font-semibold tabular-nums">{summaryValue(key)}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </section>

      {/* Budget status table */}
      <section aria-label={t("financeLite.budgetTitle")} className="flex flex-col gap-2">
        <h2 className="text-lg font-semibold">{t("financeLite.budgetTitle")}</h2>
        {budgets.isPending && <div className="h-40 animate-pulse rounded-lg bg-muted" />}
        {budgets.isError && <p role="alert" className="text-danger">{t("errors.generic")}</p>}
        {budgets.isSuccess && !budgetRows.length && <p className="text-muted-foreground">{t("financeLite.empty")}</p>}
        {budgetRows.length > 0 && (
          <Card className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-sm" data-testid="budget-table">
              <thead className="border-b bg-muted/50 text-left text-xs text-muted-foreground">
                <tr>
                  {(["department", "allocated", "spent", "utilization", "status"] as const).map((c) => (
                    <th key={c} scope="col" className={cn("px-3 py-2 font-medium", (c === "allocated" || c === "spent" || c === "utilization") && "text-right")}>{t(`financeLite.budgetCol.${c}`)}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y">
                {budgetRows.map((b) => (
                  <tr key={b.budget_id} data-testid="budget-row" data-status={b.status}>
                    <td className="px-3 py-2 font-mono text-xs">{b.department_id.slice(0, 8)}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{formatMoneyShort(b.allocated_amount, locale)}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{formatMoneyShort(b.spent_amount, locale)}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{formatPct(b.budget_utilization_pct, locale)}</td>
                    <td className={cn("px-3 py-2 font-medium", STATUS_CLASS[b.status])}>{t(`financeLite.budgetStatus.${b.status}`)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        )}
      </section>

      {/* Runway what-if readout */}
      <section aria-label={t("financeLite.runwayTitle")} className="flex flex-col gap-2">
        <h2 className="text-lg font-semibold">{t("financeLite.runwayTitle")}</h2>
        {runway.isPending && <div className="h-28 animate-pulse rounded-lg bg-muted" />}
        {runway.isError && <p role="alert" className="text-danger">{t("errors.generic")}</p>}
        {runway.isSuccess && !runwayData && <p className="text-muted-foreground">{t("financeLite.empty")}</p>}
        {runwayData && (
          <Card>
            <CardContent className="grid grid-cols-1 gap-4 pt-4 sm:grid-cols-3">
              <div data-testid="runway-value">
                <p className="text-sm text-muted-foreground">{t("financeLite.runway.months")}</p>
                <p className="text-2xl font-semibold tabular-nums">
                  {runwayData.runway_months === null ? t("financeLite.runway.noBurn") : t("financeLite.monthsValue", { value: formatNumber(runwayData.runway_months, locale, 1) })}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">{t("financeLite.runway.cashBalance")}</p>
                <p className="text-2xl font-semibold tabular-nums">{runwayData.closing_balance === null ? "—" : formatMoney(runwayData.closing_balance, locale)}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">{t("financeLite.runway.netBurn")}</p>
                <p className="text-2xl font-semibold tabular-nums">{runwayData.net_burn === null ? "—" : formatMoneyShort(runwayData.net_burn, locale)}</p>
              </div>
            </CardContent>
          </Card>
        )}
      </section>
    </div>
  );
}

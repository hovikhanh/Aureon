"use client";
import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { apiRequest } from "@/lib/api-client";
import { formatMoneyShort, formatPct, type AppLocale } from "@/lib/format";
import { qk } from "@/lib/query-keys";
import { cn } from "@/lib/utils";
import { DIMMED_STAGES, orderStages, type DealStage, type PipelineOut, type SalesDashboardOut } from "./pipeline";
import { QueryError } from "@/components/QueryError";

const SUMMARY_KEYS = ["pipeline_value", "weighted_pipeline", "win_rate_pct", "deals_open"] as const;
type SummaryKey = (typeof SUMMARY_KEYS)[number];

/**
 * M2.2 Sales pipeline kanban (T-715F, SCR-46). One column per stage from `/sales/pipeline`.
 * `closed_lost` is kept on the board but shown dimmed (not excluded) so the column still reflects
 * total deal flow; the summary strip comes from `/sales/dashboard`.
 */
export function SalesPipelineView() {
  const t = useTranslations();
  const locale = useLocale() as AppLocale;

  const pipeline = useQuery({
    queryKey: qk.salesPipeline(),
    queryFn: ({ signal }) => apiRequest<PipelineOut>("/sales/pipeline", { signal }),
  });
  const dash = useQuery({
    queryKey: qk.salesDashboard(),
    queryFn: ({ signal }) => apiRequest<SalesDashboardOut>("/sales/dashboard", { signal }),
  });

  const stages = pipeline.data ? orderStages(pipeline.data.data.stages) : [];
  const summary = dash.data?.data.summary;

  function summaryValue(key: SummaryKey): string {
    if (!summary) return "—";
    switch (key) {
      case "pipeline_value":
        return formatMoneyShort(summary.pipeline_value, locale);
      case "weighted_pipeline":
        return formatMoneyShort(summary.weighted_pipeline, locale);
      case "win_rate_pct":
        return summary.win_rate_pct === null ? "—" : formatPct(summary.win_rate_pct, locale);
      case "deals_open":
        return String(summary.deals_open);
    }
  }

  return (
    <div className="mx-auto flex max-w-[1400px] flex-col gap-6" data-testid="sales-pipeline">
      <h1 className="text-2xl font-semibold">{t("sales.title")}</h1>

      {/* Summary strip */}
      <section aria-label={t("sales.summaryTitle")}>
        {dash.isPending && <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">{SUMMARY_KEYS.map((k) => <div key={k} className="h-24 animate-pulse rounded-lg bg-muted" />)}</div>}
        {dash.isError && <QueryError error={dash.error} onRetry={() => void dash.refetch()} />}
        {dash.isSuccess && !summary && <p className="text-muted-foreground">{t("sales.empty")}</p>}
        {summary && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {SUMMARY_KEYS.map((key) => (
              <Card key={key} data-testid={`sales-summary-${key}`}>
                <CardContent className="pt-4">
                  <p className="text-sm text-muted-foreground">{t(`sales.summary.${key}`)}</p>
                  <p className="text-2xl font-semibold tabular-nums">{summaryValue(key)}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </section>

      {/* Kanban board */}
      <section aria-label={t("sales.boardTitle")} className="flex flex-col gap-2">
        {pipeline.isPending && <div className="h-64 animate-pulse rounded-lg bg-muted" />}
        {pipeline.isError && <QueryError error={pipeline.error} onRetry={() => void pipeline.refetch()} />}
        {pipeline.isSuccess && !stages.length && <p className="text-muted-foreground">{t("sales.empty")}</p>}
        {stages.length > 0 && (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
            {stages.map((s) => {
              const dimmed = DIMMED_STAGES.includes(s.stage as DealStage);
              return (
                <Card key={s.stage} data-testid={`pipeline-col-${s.stage}`} className={cn("flex flex-col", dimmed && "opacity-60")}>
                  <CardHeader>
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm font-semibold">{t(`sales.stage.${s.stage}`)}</span>
                      <span className="rounded-full bg-muted px-2 py-0.5 text-xs tabular-nums" data-testid={`pipeline-col-count-${s.stage}`}>{s.count}</span>
                    </div>
                    <p className="text-xs tabular-nums text-muted-foreground">{formatMoneyShort(s.value, locale)}</p>
                  </CardHeader>
                  <CardContent className="mt-auto">
                    <p className="text-xs text-muted-foreground">
                      {t("sales.weighted")}: <span className="tabular-nums">{formatMoneyShort(s.weighted_value, locale)}</span>
                    </p>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}

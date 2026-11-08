"use client";
/**
 * Sales analytics on `/business/sales` (funnel FUN-001/002/003, forecast FC-001/002, performance
 * PERF-004/005/007): cumulative funnel from `/sales/funnel` (D-09), weighted forecast of a quarter,
 * and owner ranking vs quota. Numbers come from the API; owner ranking needs `sales:read` in
 * khối C (`require_detail_reader`).
 */
import * as React from "react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { useQuery } from "@tanstack/react-query";
import { Card } from "@/components/ui/card";
import { NativeSelect } from "@/components/ui/select";
import { QueryError } from "@/components/QueryError";
import { apiRequest } from "@/lib/api-client";
import { formatMoney, formatMoneyShort, type AppLocale } from "@/lib/format";
import { forecast, funnelPct, quarterOptions, type FunnelOut } from "./crm";
import { business_today } from "./today";
import { crmKeys, usePerformance, usePipeline } from "./use-crm";

function useFunnel() {
  return useQuery({
    queryKey: [...crmKeys.all, "funnel"],
    queryFn: ({ signal }) => apiRequest<FunnelOut>("/sales/funnel", { signal }).then((r) => r.data),
  });
}

export function SalesInsights({ canSeeDeals, userId }: { canSeeDeals: boolean; userId: string }) {
  const t = useTranslations();
  const locale = useLocale() as AppLocale;
  const quarters = React.useMemo(() => quarterOptions(business_today()), []);
  const [quarter, setQuarter] = React.useState(quarters[1]!);
  const funnel = useFunnel();
  const period = usePipeline(quarter);
  const perf = usePerformance(quarter, canSeeDeals);
  const f = forecast(period.data?.stages ?? []);
  return (
    <div className="flex flex-col gap-4" data-testid="sales-insights">
      {canSeeDeals && (
        <nav className="flex flex-wrap gap-3 text-sm">
          <Link href="/business/sales/pipeline" className="text-primary hover:underline" data-testid="sales-open-pipeline">{t("crm.pipelineTitle")} →</Link>
          <Link href="/business/sales/records?tab=clients" className="text-primary hover:underline">{t("crm.clients")} →</Link>
        </nav>
      )}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="p-4" data-testid="sales-funnel">
          <h2 className="text-sm font-semibold">{t("salesFunnel.title")}</h2>
          {funnel.isError && <QueryError error={funnel.error} />}
          <table className="mt-2 w-full text-sm">
            <thead className="text-left text-xs text-muted-foreground"><tr><th className="py-1">{t("crm.stage")}</th><th className="text-right">{t("salesFunnel.reached")}</th><th className="text-right">{t("crm.value")}</th><th className="text-right">{t("crm.conversion")}</th><th className="text-right">{t("crm.dropOff")}</th></tr></thead>
            <tbody className="divide-y">
              {(funnel.data?.steps ?? []).map((s) => (
                <tr key={s.stage} data-testid="funnel-row" data-stage={s.stage}>
                  <td className="py-1">{t(`sales.stage.${s.stage}` as "sales.stage.lead")}</td>
                  <td className="text-right tabular-nums">{s.reached}</td>
                  <td className="text-right tabular-nums">{formatMoneyShort(s.value, locale)}</td>
                  <td className="text-right tabular-nums">{funnelPct(s.conversion_pct)}</td>
                  <td className="text-right tabular-nums">{funnelPct(s.drop_off_pct)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-2 text-xs text-muted-foreground">{t("salesFunnel.note", { lost: funnel.data?.lost ?? 0 })}</p>
        </Card>
        <Card className="p-4" data-testid="sales-forecast">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-sm font-semibold">{t("crm.forecastTitle")}</h2>
            <NativeSelect value={quarter} onChange={(e) => setQuarter(e.target.value)} aria-label={t("crm.period")} className="h-8 w-32 text-xs" data-testid="forecast-period">
              {quarters.map((q) => <option key={q} value={q}>{q}</option>)}
            </NativeSelect>
          </div>
          {period.isError && <QueryError error={period.error} />}
          <dl className="mt-3 grid grid-cols-2 gap-3 text-sm">
            {([["pipeline", f.pipeline], ["weightedPipeline", f.weighted], ["closedWon", f.closedWon], ["expected", f.expected]] as const).map(([k, v]) => (
              <div key={k}><dt className="text-muted-foreground">{t(`crm.forecast.${k}`)}</dt><dd className="font-semibold tabular-nums" data-testid={`forecast-${k}`}>{formatMoney(v, locale)}</dd></div>
            ))}
          </dl>
          <p className="mt-2 text-xs text-muted-foreground">{t("crm.forecastNote")}</p>
        </Card>
      </div>
      {canSeeDeals && (
        <Card className="p-4" data-testid="sales-ranking">
          <h2 className="text-sm font-semibold">{t("crm.rankingTitle", { period: quarter })}</h2>
          {perf.isError && <QueryError error={perf.error} />}
          {perf.isSuccess && !perf.data.length && <p className="mt-2 text-sm text-muted-foreground">{t("crm.noRanking")}</p>}
          <table className="mt-2 w-full text-sm">
            <thead className="text-left text-xs text-muted-foreground"><tr><th className="py-1">#</th><th>{t("crm.owner")}</th><th className="text-right">{t("crm.wonValue")}</th><th className="text-right">{t("crm.quota")}</th><th className="text-right">{t("crm.attainment")}</th><th className="text-right">{t("crm.winRate")}</th></tr></thead>
            <tbody className="divide-y">
              {[...(perf.data ?? [])].sort((a, b) => b.closed_value - a.closed_value).map((r, i) => (
                <tr key={r.owner_ref} data-testid="ranking-row">
                  <td className="py-1">{i + 1}</td>
                  <td>{r.owner_ref === userId ? t("crm.me") : r.owner_ref.slice(0, 8)}</td>
                  <td className="text-right tabular-nums">{formatMoneyShort(r.closed_value, locale)}</td>
                  <td className="text-right tabular-nums">{r.quota === null ? "—" : formatMoneyShort(r.quota, locale)}</td>
                  <td className="text-right tabular-nums">{r.attainment_pct === null ? "—" : `${r.attainment_pct}%`}</td>
                  <td className="text-right tabular-nums">{r.win_rate_pct === null ? "—" : `${r.win_rate_pct}%`}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}

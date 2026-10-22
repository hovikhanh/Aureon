"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/components/ui/toast";
import { api, apiRequest } from "@/lib/api-client";
import { formatMetric, type AppLocale } from "@/lib/format";
import { qk } from "@/lib/query-keys";
import type { AlertOut, MetricValue } from "./types";

const SEVERITY_RANK = { critical: 0, warning: 1 } as const;

/** Sort: critical first, then newest. */
export function sortAlerts(alerts: AlertOut[]): AlertOut[] {
  return [...alerts].sort(
    (a, b) => SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity] || b.raised_at.localeCompare(a.raised_at),
  );
}

function useAge() {
  const t = useTranslations("dashboard");
  return (iso: string) => {
    const hours = Math.max(0, Math.floor((Date.now() - new Date(iso).getTime()) / 3_600_000));
    return hours >= 48 ? t("ageDays", { days: Math.floor(hours / 24) }) : t("age", { hours });
  };
}

export function AlertsList({ units, canWrite }: { units: Record<string, string>; canWrite: boolean }) {
  const t = useTranslations();
  const locale = useLocale() as AppLocale;
  const age = useAge();
  const toast = useToast();
  const client = useQueryClient();
  const query = useQuery({
    queryKey: qk.alerts(),
    queryFn: ({ signal }) => apiRequest<AlertOut[]>("/dashboard/alerts", { query: { limit: 100 }, signal }).then((r) => r.data),
    refetchInterval: 60_000,
  });
  const ack = useMutation({
    mutationFn: (id: string) => api.post<AlertOut>(`/dashboard/alerts/${id}/acknowledge`, {}),
    onSuccess: (updated) => {
      client.setQueryData<AlertOut[]>(qk.alerts(), (xs) => xs?.map((a) => (a.id === updated.id ? updated : a)));
      toast.push(t("dashboard.acknowledged"));
    },
    onError: () => toast.push(t("errors.generic"), "danger"),
  });
  const alerts = sortAlerts((query.data ?? []).filter((a) => a.status === "open" || a.status === "acknowledged"));
  const fmt = (code: string, v: number | null) => {
    const unit = units[code] ?? "COUNT";
    return formatMetric(v, unit, locale, unit === "PCT" || unit === "VND" ? "" : t(`unit.${unit}` as "unit.DAYS"));
  };

  return (
    <Card data-testid="alerts">
      <CardHeader>
        <CardTitle>{t("dashboard.alertsTitle", { count: alerts.length })}</CardTitle>
      </CardHeader>
      <CardContent>
        {query.isPending && <div className="h-24 animate-pulse rounded bg-muted" />}
        {query.isError && (
          <div className="flex items-center gap-3 text-sm text-danger">
            {t("dashboard.alertsError")}
            <Button size="sm" variant="outline" onClick={() => void query.refetch()}>{t("buttons.retry")}</Button>
          </div>
        )}
        {query.isSuccess && alerts.length === 0 && <p className="text-sm text-muted-foreground">{t("dashboard.alertsEmpty")}</p>}
        <ul className="divide-y">
          {alerts.map((a) => (
            <li key={a.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 py-3" data-testid="alert-row" data-severity={a.severity}>
              <Badge variant={a.severity === "critical" ? "danger" : "warning"}>
                <span aria-hidden>{a.severity === "critical" ? "○" : "◐"}</span>
                {t(`dashboard.severity.${a.severity}`)}
              </Badge>
              <span className="min-w-0 flex-1 text-sm font-medium">
                {t("dashboard.alertTitle", {
                  metric: t(`metric.${a.metric_code}` as "metric.METRIC-FIN-01"),
                  value: fmt(a.metric_code, a.value),
                  threshold: fmt(a.metric_code, a.threshold),
                })}
              </span>
              {a.pillar && <Badge variant="outline">{a.pillar} · {t(`pillar.${a.pillar}.name`)}</Badge>}
              <span className="text-xs text-muted-foreground tabular-nums">{age(a.raised_at)}</span>
              {a.status === "acknowledged" ? (
                <span className="text-xs text-success">✓ {t("dashboard.acknowledged")}</span>
              ) : (
                canWrite && (
                  <Button size="sm" variant="outline" disabled={ack.isPending && ack.variables === a.id} onClick={() => ack.mutate(a.id)}>
                    {t("buttons.acknowledge")}
                  </Button>
                )
              )}
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

export function unitsOf(metrics: MetricValue[]): Record<string, string> {
  return Object.fromEntries(metrics.map((m) => [m.metric_code, m.unit]));
}

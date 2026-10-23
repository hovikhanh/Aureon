"use client";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { AlertTriangle, ChevronRight } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/StatusBadge";
import { Sparkline } from "@/components/Sparkline";
import { formatMetric, type AppLocale } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { PillarDef } from "./pillars";
import { usePeriod } from "./period";
import { usePillar } from "./use-pillar";

const RING = { ok: "border-t-success", warning: "border-t-warning", critical: "border-t-danger", no_data: "border-t-border", unavailable: "border-t-border" } as const;

export function PillarCard({ def, period, permissions }: { def: PillarDef; period: string; permissions: readonly string[] }) {
  const t = useTranslations();
  const locale = useLocale() as AppLocale;
  const view = usePillar(def, period, permissions);
  const { withPeriod } = usePeriod();
  const name = t(`pillar.${def.code}.name`);
  const top = view.metrics.find((m) => m.metric_code === def.top) ?? view.metrics[0];

  if (view.loading) {
    return <Card className="h-48 animate-pulse bg-muted" data-testid={`pillar-${def.code}`} aria-busy="true" />;
  }
  if (view.status === "unavailable") {
    return (
      <Card className="flex h-full flex-col gap-3 border-t-4 border-t-border p-4" data-testid={`pillar-${def.code}`} data-status="unavailable">
        <div className="flex items-center justify-between gap-2">
          <h2 className="font-semibold"><span className="text-muted-foreground">{def.code}</span> · {name}</h2>
          <StatusBadge status="unavailable" />
        </div>
        <p className="flex items-center gap-2 text-sm text-muted-foreground"><AlertTriangle className="h-4 w-4" aria-hidden />{t("dashboard.unavailable")}</p>
        <Button variant="outline" size="sm" className="mt-auto self-start" onClick={view.refetch}>{t("buttons.retry")}</Button>
      </Card>
    );
  }
  return (
    <Link href={withPeriod(`/home/pillar/${def.slug}`)} aria-label={t("dashboard.drillDown", { pillar: name })} className="group block h-full rounded-lg" data-testid={`pillar-${def.code}`} data-status={view.status}>
      <Card className={cn("flex h-full flex-col gap-3 border-t-4 p-4 transition-shadow group-hover:shadow-md", RING[view.status])}>
        <div className="flex items-start justify-between gap-2">
          <h2 className="font-semibold leading-tight"><span className="text-muted-foreground">{def.code}</span> · {name}</h2>
          <StatusBadge status={view.status} />
        </div>
        {top && (
          <div data-metric>
            <div className="text-xs text-muted-foreground">{t(`metric.${top.metric_code}` as "metric.METRIC-FIN-01")}</div>
            <div className="text-2xl font-semibold tabular-nums" data-testid="top-metric">
              {formatMetric(top.value, top.unit, locale, t(`unit.${top.unit}` as "unit.DAYS"))}
            </div>
          </div>
        )}
        <Sparkline values={view.series} label={t("dashboard.sparkline")} />
        <div className="mt-auto flex items-center justify-between text-xs text-muted-foreground">
          <span>{t("dashboard.openAlerts", { count: view.openAlerts })}</span>
          <ChevronRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" aria-hidden />
        </div>
      </Card>
    </Link>
  );
}

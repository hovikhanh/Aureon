"use client";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { ArrowLeft } from "lucide-react";
import { Card } from "@/components/ui/card";
import { StatusBadge } from "@/components/StatusBadge";
import { formatMetric, type AppLocale } from "@/lib/format";
import { PeriodPicker } from "./PeriodPicker";
import { usePeriod } from "./period";
import type { PillarDef } from "./pillars";
import { usePillar } from "./use-pillar";

/** S5a stub of SCR-02..06 drill-down (full screens = S5b): status + metric list. */
export function PillarDetailView({ def, permissions }: { def: PillarDef; permissions: string[] }) {
  const t = useTranslations();
  const locale = useLocale() as AppLocale;
  const { period, withPeriod } = usePeriod();
  const view = usePillar(def, period, permissions);
  const name = t(`pillar.${def.code}.name`);
  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-4" data-testid="pillar-detail" data-pillar={def.code}>
      <Link href={withPeriod("/dashboard")} className="flex items-center gap-1 text-sm text-primary"><ArrowLeft className="h-4 w-4" />{t("buttons.back")}</Link>
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-semibold">{t("dashboard.pillarPageTitle", { pillar: `${def.code} · ${name}` })}</h1>
        {!view.loading && <StatusBadge status={view.status} />}
      </div>
      <PeriodPicker />
      <p className="text-sm text-muted-foreground">{t("dashboard.pillarPagePending")}</p>
      <Card className="divide-y">
        <h2 className="p-4 font-semibold">{t("dashboard.metricsOfPillar")}</h2>
        {view.metrics.map((m) => (
          <div key={m.metric_code} className="flex items-center justify-between gap-3 p-4" data-metric>
            <span className="text-sm">{t(`metric.${m.metric_code}` as "metric.METRIC-FIN-01")}</span>
            <span className="flex items-center gap-3">
              <span className="font-semibold tabular-nums">{formatMetric(m.value, m.unit, locale, t(`unit.${m.unit}` as "unit.DAYS"))}</span>
              <StatusBadge status={m.status} />
            </span>
          </div>
        ))}
      </Card>
    </div>
  );
}

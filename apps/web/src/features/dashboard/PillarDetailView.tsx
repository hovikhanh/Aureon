"use client";
import { useState } from "react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { ArrowLeft } from "lucide-react";
import { Card } from "@/components/ui/card";
import { StatusBadge } from "@/components/StatusBadge";
import { formatMetric, type AppLocale } from "@/lib/format";
import { MetricDetailPanel } from "./MetricDetailPanel";
import { PeriodPicker } from "./PeriodPicker";
import { usePeriod } from "./period";
import type { PillarDef } from "./pillars";
import { usePillar } from "./use-pillar";

/** SCR-02..06 pillar drill-down: metric list where every number opens the EP-12 detail (P01). */
export function PillarDetailView({ def, permissions }: { def: PillarDef; permissions: string[] }) {
  const t = useTranslations();
  const locale = useLocale() as AppLocale;
  const { period, withPeriod } = usePeriod();
  const view = usePillar(def, period, permissions);
  const name = t(`pillar.${def.code}.name`);
  const [openCode, setOpenCode] = useState<string | null>(null);
  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-4" data-testid="pillar-detail" data-pillar={def.code}>
      <Link href={withPeriod("/home")} className="flex items-center gap-1 text-sm text-primary"><ArrowLeft className="h-4 w-4" />{t("buttons.back")}</Link>
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
              <button
                type="button"
                onClick={() => setOpenCode(m.metric_code)}
                className="rounded font-semibold tabular-nums text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                data-testid="metric-open"
                data-code={m.metric_code}
                aria-label={t("dashboard.openMetric", { metric: t(`metric.${m.metric_code}` as "metric.METRIC-FIN-01") })}
              >
                {formatMetric(m.value, m.unit, locale, t(`unit.${m.unit}` as "unit.DAYS"))}
              </button>
              <StatusBadge status={m.status} />
            </span>
          </div>
        ))}
      </Card>
      <MetricDetailPanel code={openCode} onClose={() => setOpenCode(null)} />
    </div>
  );
}

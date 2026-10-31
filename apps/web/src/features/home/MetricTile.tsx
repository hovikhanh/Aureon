"use client";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { Card } from "@/components/ui/card";
import { StatusBadge } from "@/components/StatusBadge";
import { formatMetric, type AppLocale } from "@/lib/format";
import type { CardStatus } from "@/features/dashboard/types";
import type { MetricValue } from "./types";

/** SCR-40 ô chỉ số — số click được tới P01/lineage (BRD-P01); nhãn "cũ" khi is_stale. */
export function MetricTile({ m }: { m: MetricValue }) {
  const locale = useLocale() as AppLocale;
  const t = useTranslations("metric");
  return (
    <Card className="flex flex-col gap-2 p-4" data-testid="metric-tile" data-code={m.metric_code}>
      <div className="flex items-start justify-between gap-2">
        <Link href={m.lineage_url} className="text-sm font-medium text-muted-foreground hover:text-primary hover:underline">
          {t(m.metric_code)}
        </Link>
        <StatusBadge status={m.status as CardStatus} />
      </div>
      <div className="text-2xl font-semibold tabular-nums">{formatMetric(m.value, m.unit, locale)}</div>
      {m.is_stale && (
        <span className="text-xs text-amber-600" data-testid="stale-flag">
          {t("stale", { hours: m.max_age_hours })}
        </span>
      )}
    </Card>
  );
}

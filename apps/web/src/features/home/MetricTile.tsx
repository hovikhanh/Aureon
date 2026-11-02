"use client";
import { useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Card } from "@/components/ui/card";
import { StatusBadge } from "@/components/StatusBadge";
import { MetricDetailPanel } from "@/features/dashboard/MetricDetailPanel";
import { formatMetric, type AppLocale } from "@/lib/format";
import type { CardStatus } from "@/features/dashboard/types";
import type { MetricValue } from "./types";

/**
 * SCR-40 ô chỉ số — số/nhãn click được mở drill-down EP-12 (BRD-P01); nhãn "cũ" khi is_stale.
 * Panel tự chứa link lineage, nên không điều hướng thẳng tới `lineage_url` (đường dẫn API, không
 * phải page route) — tránh 404 khi bấm tile.
 */
export function MetricTile({ m }: { m: MetricValue }) {
  const locale = useLocale() as AppLocale;
  const t = useTranslations("metric");
  const td = useTranslations("dashboard");
  const [open, setOpen] = useState(false);
  const label = t(m.metric_code as "METRIC-FIN-01");
  return (
    <Card className="flex flex-col gap-2 p-4" data-testid="metric-tile" data-code={m.metric_code}>
      <div className="flex items-start justify-between gap-2">
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="rounded text-left text-sm font-medium text-muted-foreground hover:text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          data-testid="metric-open"
          data-code={m.metric_code}
          aria-label={td("openMetric", { metric: label })}
        >
          {label}
        </button>
        <StatusBadge status={m.status as CardStatus} />
      </div>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="rounded text-left text-2xl font-semibold tabular-nums hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        data-testid="metric-value"
        aria-label={td("openMetric", { metric: label })}
      >
        {formatMetric(m.value, m.unit, locale)}
      </button>
      {m.is_stale && (
        <span className="text-xs text-amber-600" data-testid="stale-flag">
          {t("stale", { hours: m.max_age_hours })}
        </span>
      )}
      <MetricDetailPanel code={open ? m.metric_code : null} onClose={() => setOpen(false)} />
    </Card>
  );
}

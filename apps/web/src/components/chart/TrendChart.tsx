"use client";

import { useMemo } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useTranslations } from "next-intl";
import type { TrendChartProps } from "@/features/dashboard/types";
import { formatMetricValue } from "@/features/dashboard/format-metric";
import { useP04Formatter } from "@/lib/use-p04-formatter";
import { cn } from "@/lib/utils";

/**
 * TrendChart — metric trend over periods (06 §4.1, §6.6; EP-12 `history[]`), Recharts (DEC-064).
 *
 * Accessibility (06 §9): the SVG chart is decorative (`aria-hidden`); the real semantics live
 * in a visually-hidden `<table>` fallback + an `aria-describedby` summary, so screen readers
 * (and jsdom tests) get the data without a canvas. Axis ticks and the tooltip are formatted
 * through the P04 formatter (06 §7.1) — period keys → `T9/2026`/`Q3/2026`, values via the
 * metric's `formatKind`. NO_DATA / NOT_COMPUTABLE points are rendered as gaps (null), and when
 * no point is plottable the component shows the "no trend data" empty text instead of an
 * empty chart. All copy is i18n (06 §7.2, TC-UI-005).
 *
 * In jsdom tests pass fixed `width`/`height` for deterministic layout (ResponsiveContainer
 * needs a measured parent). In the app it defaults to a responsive 100%×h-64 container.
 */
export function TrendChart(props: TrendChartProps) {
  const { metricCode, nameI18nKey, formatKind, history, width, height } = props;
  const t = useTranslations("chart");
  const tMetric = useTranslations("metric");
  const tRoot = useTranslations();
  const fmt = useP04Formatter();
  const units = useMemo(
    () => ({
      days: tMetric("unit.days"),
      months: tMetric("unit.months"),
      tasksPerPerson: tMetric("unit.tasksPerPerson"),
      vndPerPerson: tMetric("unit.vndPerPerson"),
    }),
    [tMetric],
  );

  const name = nameI18nKey && tRoot.has(nameI18nKey) ? tRoot(nameI18nKey) : metricCode;

  const rows = useMemo(
    () =>
      history.map((p) => ({
        periodKey: p.period_key,
        periodLabel: fmt.period(p.period_key),
        // Only OK points carry a plottable number (10 §1.9).
        value: p.value_state === "OK" ? p.value : null,
        target: p.target_value,
        valueState: p.value_state,
        valueText:
          p.value_state === "OK" && typeof p.value === "number"
            ? formatMetricValue(fmt, formatKind, p.value, units)
            : t("notComputable"),
        targetText:
          typeof p.target_value === "number"
            ? formatMetricValue(fmt, formatKind, p.target_value, units)
            : fmt.number(null),
      })),
    [history, fmt, formatKind, units, t],
  );

  const plottable = rows.filter((r) => typeof r.value === "number");
  const hasData = plottable.length > 0;
  const summaryId = `trend-summary-${metricCode}`;
  const title = t("title", { name });

  // Empty / all-null → show the empty text (06 §4.1 "Empty"), never a blank chart.
  if (!hasData) {
    return (
      <figure
        data-trend-chart={metricCode}
        data-empty="true"
        aria-label={title}
        className="flex min-h-40 flex-col items-center justify-center gap-1 rounded-lg border border-dashed border-border p-6 text-center"
      >
        <figcaption className="text-caption text-neutral-500">{t("empty")}</figcaption>
      </figure>
    );
  }

  const first = plottable[0];
  const last = plottable[plottable.length - 1];
  const summary = t("summary", { name, first: first.periodLabel, last: last.periodLabel });

  return (
    <figure data-trend-chart={metricCode} aria-describedby={summaryId} className="flex flex-col gap-2">
      <figcaption className="text-caption font-medium text-foreground">{title}</figcaption>
      <p id={summaryId} className="sr-only">
        {summary}
      </p>

      {/* Decorative visual chart; semantics are in the table fallback below. */}
      <div aria-hidden="true" style={width && height ? { width, height } : undefined} className={cn(!height && "h-64 w-full")}>
        <ResponsiveContainer width={width ?? "100%"} height={height ?? "100%"}>
          <LineChart data={rows} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-neutral-200)" />
            <XAxis dataKey="periodLabel" tick={{ fontSize: 12 }} stroke="var(--color-neutral-500)" />
            <YAxis
              tick={{ fontSize: 12 }}
              stroke="var(--color-neutral-500)"
              tickFormatter={(v: unknown) =>
                typeof v === "number" ? formatMetricValue(fmt, formatKind, v, units) : String(v ?? "")
              }
              width={72}
            />
            <Tooltip
              formatter={(v: unknown) => [
                typeof v === "number" ? formatMetricValue(fmt, formatKind, v, units) : String(v ?? ""),
                name,
              ]}
              labelFormatter={(label: unknown) => String(label ?? "")}
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke="var(--color-primary)"
              strokeWidth={2}
              connectNulls={false}
              dot={{ r: 3 }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Screen-reader / test data table fallback (P01: every point readable). */}
      <table className="sr-only">
        <caption>{t("tableCaption", { name })}</caption>
        <thead>
          <tr>
            <th scope="col">{t("columnPeriod")}</th>
            <th scope="col">{t("columnValue")}</th>
            <th scope="col">{t("columnTarget")}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.periodKey} data-period={r.periodKey} data-value-state={r.valueState}>
              <th scope="row">{r.periodLabel}</th>
              <td>{r.valueText}</td>
              <td>{r.targetText}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}

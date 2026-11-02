"use client";
import { useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Database, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { StatusBadge } from "@/components/StatusBadge";
import { formatMetric, formatPeriod, type AppLocale } from "@/lib/format";
import { chartSeries, hasTrend } from "./metric-detail";
import type { CardStatus } from "./types";
import { useMetricDetail } from "./use-metric-detail";

/**
 * SCR-12 metric drill-down (06 P01): EP-12 detail — value + status, formula, trend line with
 * threshold reference lines, component breakdown (with record counts), related alerts, and the
 * lineage link closing the "every number is clickable" loop. One query per open panel.
 */
export function MetricDetailPanel({ code, onClose }: { code: string | null; onClose: () => void }) {
  const t = useTranslations("metricDetail");
  const tm = useTranslations("metric");
  const locale = useLocale() as AppLocale;
  const open = Boolean(code);
  const { detail, loading, error, refetch } = useMetricDetail(code);
  const [showLineage, setShowLineage] = useState(false);

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        if (!o) {
          setShowLineage(false);
          onClose();
        }
      }}
    >
      <DialogContent className="max-w-2xl" data-testid="metric-detail-panel" data-code={code ?? undefined}>
        {!detail && (
          <>
            {/* Radix a11y: DialogTitle/Description luôn có mặt, kể cả khi đang tải / lỗi. */}
            <DialogTitle className="sr-only">{t("title")}</DialogTitle>
            <DialogDescription className="sr-only">{error ? t("error") : t("loading")}</DialogDescription>
          </>
        )}
        {loading && <p className="py-8 text-center text-sm text-muted-foreground">{t("loading")}</p>}
        {error && (
          <div className="flex items-center justify-between gap-3 py-6 text-sm">
            {t("error")}
            <Button variant="outline" size="sm" onClick={refetch}>{t("retry")}</Button>
          </div>
        )}
        {detail && (
          <div className="flex flex-col gap-5">
            <div>
              <DialogTitle className="flex flex-wrap items-center gap-3 text-xl">
                {detail.name}
                <StatusBadge status={detail.status as CardStatus} />
              </DialogTitle>
              <DialogDescription className="mt-1 flex flex-wrap items-baseline gap-3">
                <span className="text-2xl font-semibold tabular-nums text-foreground" data-testid="metric-detail-value">
                  {formatMetric(detail.value, detail.unit, locale)}
                </span>
                {detail.period_key && <span className="text-xs text-muted-foreground">{formatPeriod(detail.period_key, locale)}</span>}
                {detail.is_stale && (
                  <span className="text-xs text-amber-600" data-testid="metric-detail-stale">
                    {t("stale", { hours: detail.max_age_hours ?? 24 })}
                  </span>
                )}
              </DialogDescription>
            </div>

            <section className="rounded-md border bg-muted/40 p-3 text-sm">
              <span className="font-medium">{t("formula")}:</span> <span className="font-mono text-xs">{detail.formula_display}</span>
              <div className="mt-1 text-xs text-muted-foreground">
                {t("thresholds")}: {t("warning")} {detail.thresholds.warning} · {t("critical")} {detail.thresholds.critical} ·{" "}
                {detail.direction === "up" ? t("directionUp") : t("directionDown")}
              </div>
            </section>

            <section data-testid="metric-detail-trend">
              <h3 className="mb-2 text-sm font-semibold">{t("trend")}</h3>
              {hasTrend(detail.trend) ? (
                <div className="h-48 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartSeries(detail.trend)} margin={{ top: 8, right: 12, bottom: 4, left: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                      <XAxis dataKey="period_key" tick={{ fontSize: 11 }} tickFormatter={(k: string) => formatPeriod(k, locale)} />
                      <YAxis tick={{ fontSize: 11 }} width={44} />
                      <Tooltip labelFormatter={(k) => formatPeriod(String(k), locale)} />
                      <ReferenceLine y={detail.thresholds.warning} stroke="var(--warning)" strokeDasharray="4 4" />
                      <ReferenceLine y={detail.thresholds.critical} stroke="var(--destructive)" strokeDasharray="4 4" />
                      <Line type="monotone" dataKey="value" stroke="var(--primary)" strokeWidth={2} dot={{ r: 2 }} isAnimationActive={false} connectNulls />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">{t("trendEmpty")}</p>
              )}
            </section>

            {detail.breakdown.length > 0 && (
              <section data-testid="metric-detail-breakdown">
                <h3 className="mb-2 text-sm font-semibold">{t("breakdown")}</h3>
                <ul className="divide-y rounded-md border text-sm">
                  {detail.breakdown.map((r) => (
                    <li key={r.key} className="flex items-center justify-between gap-3 px-3 py-2">
                      <span>{r.label}</span>
                      <span className="flex items-center gap-3">
                        <span className="tabular-nums">{formatMetric(r.value, detail.unit, locale)}</span>
                        <span className="text-xs text-muted-foreground">{t("records", { count: r.record_count })}</span>
                      </span>
                    </li>
                  ))}
                </ul>
              </section>
            )}

            <section data-testid="metric-detail-alerts">
              <h3 className="mb-2 text-sm font-semibold">{t("relatedAlerts")}</h3>
              {detail.related_alerts.length === 0 ? (
                <p className="text-sm text-muted-foreground">{t("noAlerts")}</p>
              ) : (
                <ul className="flex flex-col gap-1 text-sm">
                  {detail.related_alerts.map((a) => (
                    <li key={a.id} className="flex items-center gap-2">
                      <StatusBadge status={a.severity === "critical" ? "critical" : "warning"} />
                      <span>{tm(a.metric_code as "METRIC-FIN-01")}</span>
                      <span className="text-xs text-muted-foreground tabular-nums">{a.value}</span>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <footer className="flex flex-wrap items-center justify-between gap-3 border-t pt-3 text-xs text-muted-foreground">
              <span className="flex items-center gap-1.5">
                <Database className="h-3.5 w-3.5" aria-hidden />
                {t("dataSource")}: {detail.data_source.module} · {detail.data_source.entities.join(", ")}
              </span>
              {/* lineage_url là đường dẫn API, không phải page route → không dùng <Link>/<a> (tránh prefetch/điều hướng 404). */}
              <button
                type="button"
                onClick={() => setShowLineage((v) => !v)}
                aria-expanded={showLineage}
                aria-controls="metric-detail-lineage-info"
                className="flex items-center gap-1 font-medium text-primary hover:underline"
                data-testid="metric-detail-lineage"
              >
                {t("lineage")} <ExternalLink className="h-3.5 w-3.5" aria-hidden />
              </button>
            </footer>
            {showLineage && (
              <dl id="metric-detail-lineage-info" className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 rounded-md border bg-muted/40 p-3 text-xs" data-testid="metric-detail-lineage-info">
                <dt className="text-muted-foreground">{t("lineageSource")}</dt>
                <dd>{detail.data_source.module} · {detail.data_source.entities.join(", ")}</dd>
                <dt className="text-muted-foreground">{t("lineageComputedAt")}</dt>
                <dd className="tabular-nums">{detail.computed_at}</dd>
                <dt className="text-muted-foreground">{t("lineageRef")}</dt>
                <dd className="break-all font-mono">{detail.lineage_url}</dd>
              </dl>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

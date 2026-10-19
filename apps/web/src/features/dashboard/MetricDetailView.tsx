"use client";

import { useMemo } from "react";
import Link from "next/link";
import { ArrowLeft, FileText, Lock } from "lucide-react";
import { useTranslations } from "next-intl";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/features/auth/auth-context";
import { ApiClientError } from "@/lib/api-client";
import { useP04Formatter } from "@/lib/use-p04-formatter";
import { TrendChart } from "@/components/chart/TrendChart";
import { AlertCard } from "@/components/alert/AlertCard";
import { UNIT_FORMAT_KIND } from "./types";
import { formatMetricValue } from "./format-metric";
import { getMetricDetailApi, getMetricRecordsApi } from "./dashboard-api";
import { alertToCard } from "./api-to-view";

/**
 * SCR-09 — Metric Detail drill-down (06 §4.6, 03 §4.1, EP-12/EP-13/EP-14).
 * Click 1 of the ≤3-click lineage chain: Dashboard → MetricCard → (here) → source record → doc.
 * Renders Header, LineagePanel (5 P01 parts), TrendChart, BreakdownTable, RecordPanel and the
 * bound Alert. All numbers go through the P04 formatter; no hard-coded Vietnamese (TC-UI-005).
 */
export function MetricDetailView({ metricCode }: { metricCode: string }) {
  const t = useTranslations("metricDetail");
  const tRoot = useTranslations();
  const tMetric = useTranslations("metric");
  const fmt = useP04Formatter();
  const { session } = useAuth();
  const token = session?.accessToken;

  const units = {
    days: tMetric("unit.days"),
    months: tMetric("unit.months"),
    tasksPerPerson: tMetric("unit.tasksPerPerson"),
    vndPerPerson: tMetric("unit.vndPerPerson"),
  };

  const detailQuery = useQuery({
    queryKey: ["metric-detail", metricCode],
    queryFn: () => getMetricDetailApi(metricCode, { history: 12 }, token),
    enabled: Boolean(token),
  });
  const detail = detailQuery.data;
  const access = detail?.metric.access_level ?? "FULL";

  // EP-13 source records (click 2). Only meaningful at FULL access.
  const recordsQuery = useQuery({
    queryKey: ["metric-records", metricCode, detail?.metric.period_key],
    queryFn: () =>
      getMetricRecordsApi(metricCode, { periodKey: detail?.metric.period_key }, token),
    enabled: Boolean(token && detail && access === "FULL"),
  });

  const formatKind = detail ? UNIT_FORMAT_KIND[detail.metric.unit] : "count";
  const metricName = useMemo(() => {
    const key = `metricNames.${metricCode}`;
    return tRoot.has(key) ? tRoot(key) : metricCode;
  }, [metricCode, tRoot]);

  const fmtVal = (v: number | null): string =>
    v === null ? "N/A" : formatMetricValue(fmt, formatKind, v, units);

  if (detailQuery.isLoading) {
    return <p className="p-6 text-body-sm text-muted-foreground">{t("loading")}</p>;
  }
  if (detailQuery.isError || !detail) {
    const code =
      detailQuery.error instanceof ApiClientError ? detailQuery.error.code : undefined;
    return (
      <div className="space-y-4 p-6">
        <BackLink label={t("back")} />
        <p className="rounded-lg border border-critical/30 bg-critical/5 p-4 text-body-sm text-critical">
          {t("loadError")}
          {code ? ` (${code})` : ""}
        </p>
      </div>
    );
  }

  const m = detail.metric;
  const lineage = detail.lineage_panel;

  return (
    <div className="space-y-6 pb-12">
      {/* Breadcrumb + back */}
      <nav aria-label="breadcrumb" className="flex items-center gap-2 text-caption text-muted-foreground">
        <Link href="/dashboard" className="hover:text-foreground">
          {t("breadcrumbDashboard")}
        </Link>
        <span>›</span>
        <span className="font-mono text-foreground">{metricCode}</span>
      </nav>
      <BackLink label={t("back")} />

      {/* Header */}
      <header className="space-y-1">
        <h1 className="text-h1 font-bold text-foreground">{metricName}</h1>
        <div className="flex items-baseline gap-3">
          <span className="text-h2 font-bold tabular-nums text-foreground">{fmtVal(m.value)}</span>
          {m.target_value !== null && (
            <span className="text-body-sm text-muted-foreground">
              {t("target")}: {fmtVal(m.target_value)}
            </span>
          )}
          {m.status_color && m.value_state === "OK" && (
            <span
              data-status={m.status_color}
              className="inline-flex items-center rounded-full px-2.5 py-0.5 text-caption font-bold data-[status=GREEN]:bg-success/10 data-[status=GREEN]:text-success data-[status=YELLOW]:bg-warning/10 data-[status=YELLOW]:text-warning data-[status=RED]:bg-critical/10 data-[status=RED]:text-critical"
            >
              {tMetric(`status.${statusKey(m.status_color)}`)}
            </span>
          )}
        </div>
        <p className="font-mono text-caption text-muted-foreground">{metricCode} · {fmt.period(m.period_key)}</p>
      </header>

      {/* LineagePanel — 5 P01 parts */}
      <section aria-label={t("lineageTitle")} className="rounded-xl border border-border bg-card p-5">
        <h2 className="mb-3 text-h3 font-semibold text-foreground">{t("lineageTitle")}</h2>
        <dl className="grid gap-x-6 gap-y-3 sm:grid-cols-2">
          <Field label={t("formula")} value={lineage.formula_display} mono />
          <Field label={t("computedAt")} value={lineage.computed_at ? fmt.dateTime(lineage.computed_at) : "—"} />
          <Field label={t("sourceRecordTypes")} value={lineage.source_record_types.join(", ") || "—"} />
          <Field label={t("computation")} value={lineage.computation ?? "—"} />
          {lineage.source_record_count !== null && (
            <Field label={t("sourceRecordCount")} value={String(lineage.source_record_count)} />
          )}
        </dl>

        {/* computation_inputs (numerator/denominator) — FULL only / required when NOT_COMPUTABLE */}
        {detail.computation_inputs && (
          <div className="mt-4 border-t border-border pt-3">
            <p className="mb-1 text-caption font-semibold text-muted-foreground">{t("computationInputs")}</p>
            <p className="text-body-sm tabular-nums text-foreground">
              {t("numerator")}: {fmt.number(detail.computation_inputs.numerator ?? 0, 0)} ·{" "}
              {t("denominator")}: {fmt.number(detail.computation_inputs.denominator ?? 0, 0)}
            </p>
          </div>
        )}

        {/* Source documents (FULL only) */}
        {lineage.source_documents && lineage.source_documents.length > 0 && (
          <div className="mt-4 border-t border-border pt-3">
            <p className="mb-2 text-caption font-semibold text-muted-foreground">{t("sourceDocuments")}</p>
            <ul className="space-y-1.5">
              {lineage.source_documents.map((doc) => (
                <li key={doc.id} className="flex items-center gap-2 text-body-sm">
                  {doc.restricted ? (
                    <Lock className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                  ) : (
                    <FileText className="h-4 w-4 text-ai" aria-hidden="true" />
                  )}
                  {doc.restricted ? (
                    <span className="text-muted-foreground">{t("restrictedSalary")}</span>
                  ) : (
                    <Link href={`/documents/${doc.id}`} className="text-ai hover:underline">
                      {doc.original_filename ?? doc.id}
                    </Link>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>

      {/* TrendChart */}
      {detail.history.length > 0 && (
        <section aria-label={t("trendTitle")} className="rounded-xl border border-border bg-card p-5">
          <h2 className="mb-3 text-h3 font-semibold text-foreground">{t("trendTitle")}</h2>
          <TrendChart
            metricCode={metricCode}
            nameI18nKey={`metricNames.${metricCode}`}
            formatKind={formatKind}
            history={detail.history}
          />
        </section>
      )}

      {/* BreakdownTable (null when AGG — DS2) */}
      {detail.breakdown && detail.breakdown.rows.length > 0 && (
        <section aria-label={t("breakdownTitle")} className="rounded-xl border border-border bg-card p-5">
          <h2 className="mb-3 text-h3 font-semibold text-foreground">{t("breakdownTitle")}</h2>
          <table className="w-full text-body-sm">
            <thead>
              <tr className="border-b border-border text-left text-caption text-muted-foreground">
                <th className="pb-2 font-medium">{t("breakdownKey")}</th>
                <th className="pb-2 text-right font-medium">{t("breakdownValue")}</th>
                <th className="pb-2 text-right font-medium">{t("breakdownShare")}</th>
              </tr>
            </thead>
            <tbody>
              {detail.breakdown.rows.map((r) => (
                <tr key={r.key} className="border-b border-border/50">
                  <td className="py-1.5 text-foreground">{r.label}</td>
                  <td className="py-1.5 text-right tabular-nums text-foreground">{fmtVal(r.value)}</td>
                  <td className="py-1.5 text-right tabular-nums text-muted-foreground">
                    {r.share !== null ? fmt.percent(r.share) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {/* RecordPanel (click 2) */}
      <section aria-label={t("recordsTitle")} className="rounded-xl border border-border bg-card p-5">
        <h2 className="mb-3 text-h3 font-semibold text-foreground">{t("recordsTitle")}</h2>
        {access !== "FULL" ? (
          <p className="text-body-sm text-muted-foreground">{t("aggOnly")}</p>
        ) : recordsQuery.data && recordsQuery.data.data.length > 0 ? (
          <ul className="space-y-1.5">
            {recordsQuery.data.data.map((rec) => (
              <li key={rec.id} className="flex items-center justify-between gap-2 text-body-sm">
                <span className="text-foreground">
                  <span className="font-mono text-caption text-muted-foreground">{rec.record_type}</span>{" "}
                  {rec.name ?? rec.code ?? rec.id}
                </span>
                {rec.source_document_id && (
                  <Link
                    href={`/documents/${rec.source_document_id}`}
                    className="shrink-0 text-ai hover:underline"
                  >
                    {t("openDocument")}
                  </Link>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-body-sm text-muted-foreground">{t("noRecords")}</p>
        )}
      </section>

      {/* Bound alert (metric 1-1) */}
      {detail.alert && (
        <section className="grid gap-3 sm:max-w-md">
          <AlertCard {...alertToCard(detail.alert)} />
        </section>
      )}
    </div>
  );
}

function BackLink({ label }: { label: string }) {
  return (
    <Link
      href="/dashboard"
      className="inline-flex items-center gap-1.5 text-body-sm text-ai hover:underline"
    >
      <ArrowLeft className="h-4 w-4" aria-hidden="true" />
      {label}
    </Link>
  );
}

function Field({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <dt className="text-caption font-medium text-muted-foreground">{label}</dt>
      <dd className={`text-body-sm text-foreground ${mono ? "font-mono" : ""}`}>{value}</dd>
    </div>
  );
}

function statusKey(c: "GREEN" | "YELLOW" | "RED"): "ok" | "warning" | "critical" {
  return c === "GREEN" ? "ok" : c === "YELLOW" ? "warning" : "critical";
}

"use client";
/** SCR-58 Recharts chart: actual vs target per period + NEAR / BELOW threshold lines (values from the API evaluations). */
import { useLocale, useTranslations } from "next-intl";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { formatPeriod, type AppLocale } from "@/lib/format";
import { chartRows, formatValue } from "./logic";
import type { KpiEvaluationOut } from "./use-goals";

export function KpiChart({ evaluations, direction, unit }: { evaluations: KpiEvaluationOut[]; direction: string; unit: string }) {
  const t = useTranslations("goals.kpi");
  const locale = useLocale() as AppLocale;
  const rows = chartRows(evaluations, direction);
  if (!rows.length) return <p className="text-sm text-muted-foreground" data-testid="kpi-chart-empty">{t("chartEmpty")}</p>;
  const fmt = (v: number) => formatValue(v, unit, locale);
  return (
    <figure className="h-64 w-full" data-testid="kpi-chart" aria-label={t("chart")}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={rows} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
          <XAxis dataKey="period_key" tickFormatter={(p: string) => formatPeriod(p, locale)} fontSize={12} />
          <YAxis fontSize={12} tickFormatter={fmt} width={72} />
          <Tooltip formatter={(v) => fmt(Number(v))} labelFormatter={(p) => formatPeriod(String(p), locale)} />
          <Legend />
          <Line type="monotone" dataKey="actual" name={t("actual")} stroke="var(--color-primary, #2563eb)" strokeWidth={2} dot />
          <Line type="stepAfter" dataKey="target" name={t("target")} stroke="var(--color-success, #16a34a)" strokeDasharray="6 3" dot={false} />
          <Line type="stepAfter" dataKey="near" name={t("near")} stroke="var(--color-warning, #d97706)" strokeDasharray="2 4" dot={false} />
          <Line type="stepAfter" dataKey="below" name={t("below")} stroke="var(--color-danger, #dc2626)" strokeDasharray="2 4" dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </figure>
  );
}

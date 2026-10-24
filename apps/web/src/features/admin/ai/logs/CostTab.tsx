"use client";
import * as React from "react";
import { useLocale, useTranslations } from "next-intl";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { NativeSelect } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { formatNumber, formatPct, type AppLocale } from "@/lib/format";
import { useUsage } from "../use-ai-admin";
import { COST_GROUPS, usd4 } from "./log-logic";
import { useUserNames } from "./parts";

/** SCR-65 Chi phí tab (EP-AI-15): month + group_by → Recharts bar + table. */
export function CostTab() {
  const t = useTranslations("aiLogs");
  const locale = useLocale() as AppLocale;
  const [group, setGroup] = React.useState<(typeof COST_GROUPS)[number]>("provider");
  const [period, setPeriod] = React.useState(() => new Date().toISOString().slice(0, 7));
  const u = useUsage({ group_by: group, period });
  const name = useUserNames();
  const label = (k: string) => (group === "user" ? name(k) : k);
  const rows = (u.data?.rows ?? []).map((r) => ({ ...r, label: label(r.key) }));
  return (
    <section className="flex flex-col gap-3" data-testid="cost-tab">
      <div className="flex flex-wrap items-end gap-3">
        <div className="flex flex-col gap-1"><Label htmlFor="ct-period">{t("period")}</Label>
          <Input id="ct-period" type="month" value={period} onChange={(e) => setPeriod(e.target.value)} data-testid="cost-period" /></div>
        <div className="flex flex-col gap-1"><Label htmlFor="ct-group">{t("groupBy")}</Label>
          <NativeSelect id="ct-group" value={group} onChange={(e) => setGroup(e.target.value as typeof group)} data-testid="cost-group">
            {COST_GROUPS.map((g) => <option key={g} value={g}>{t(`group.${g}`)}</option>)}
          </NativeSelect></div>
        {u.data && <p className="pb-2 text-sm" data-testid="cost-summary">{t("budget", { used: usd4(u.data.used_usd), budget: formatNumber(u.data.budget_usd, locale, 2), pct: formatPct(u.data.used_pct, locale) })}</p>}
      </div>
      {u.isError && <p role="alert" className="text-sm text-danger" data-testid="cost-error">{t("error")}</p>}
      {rows.length > 0 && (
        <figure className="h-64 w-full rounded-lg border bg-card p-2" aria-label={t("tabs.cost")} data-testid="cost-chart">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={rows} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis dataKey="label" fontSize={12} />
              <YAxis fontSize={12} tickFormatter={(v: number) => `$${v}`} width={56} />
              <Tooltip formatter={(v) => usd4(Number(v))} />
              <Bar dataKey="cost_usd" name={t("col.cost")} fill="var(--color-primary, #2563eb)" />
            </BarChart>
          </ResponsiveContainer>
        </figure>
      )}
      <div className="overflow-x-auto rounded-lg border bg-card">
        <table className="w-full text-sm">
          <thead className="bg-muted/50 text-left text-xs text-muted-foreground">
            <tr>{["key", "calls", "tokens", "cost", "errorRate", "p95"].map((c) => <th key={c} className="px-3 py-2">{t(`cost.${c}`)}</th>)}</tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.key} className="border-t" data-testid="cost-row">
                <td className="px-3 py-2">{r.label}</td>
                <td className="px-3 py-2">{formatNumber(r.calls, locale, 0)}</td>
                <td className="px-3 py-2">{formatNumber(r.tokens_in, locale, 0)} / {formatNumber(r.tokens_out, locale, 0)}</td>
                <td className="px-3 py-2 font-mono text-xs">{usd4(r.cost_usd)}</td>
                <td className="px-3 py-2">{formatPct(r.error_rate * 100, locale)}</td>
                <td className="px-3 py-2">{r.p95_ms != null ? `${formatNumber(r.p95_ms, locale, 0)} ms` : "—"}</td>
              </tr>
            ))}
            {u.isSuccess && rows.length === 0 && <tr><td colSpan={6} className="px-3 py-6 text-center text-muted-foreground">{t("empty")}</td></tr>}
          </tbody>
        </table>
      </div>
    </section>
  );
}

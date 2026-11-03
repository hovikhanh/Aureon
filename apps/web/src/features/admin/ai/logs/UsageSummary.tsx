"use client";
import { useLocale, useTranslations } from "next-intl";
import { Card } from "@/components/ui/card";
import { formatNumber, formatPct, type AppLocale } from "@/lib/format";
import { useUsage } from "../use-ai-admin";
import { usageTotals, usd4 } from "./log-logic";

/**
 * SCR-65 header strip: this month's model calls, tokens, cost and error rate from EP-AI-15 (one
 * query, `group_by=provider`), shown above every tab so the telemetry is visible even while the
 * tool-call tab is open. `unpriced_calls` > 0 → the cost is a lower bound, said out loud.
 */
export function UsageSummary() {
  const t = useTranslations("aiLogs.summary");
  const locale = useLocale() as AppLocale;
  const period = new Date().toISOString().slice(0, 7);
  const u = useUsage({ group_by: "provider", period });
  if (u.isError) return <p role="alert" className="text-sm text-danger" data-testid="usage-summary-error">{t("error")}</p>;
  const total = usageTotals(u.data?.rows ?? []);
  const tiles: [string, string, string][] = [
    ["calls", t("calls"), formatNumber(total.calls, locale, 0)],
    ["tokens", t("tokens"), `${formatNumber(total.tokensIn, locale, 0)} / ${formatNumber(total.tokensOut, locale, 0)}`],
    ["cost", t("cost"), usd4(total.costUsd)],
    ["errors", t("errors"), `${formatNumber(total.errors, locale, 0)} (${formatPct(total.errorRate * 100, locale)})`],
  ];
  return (
    <section className="flex flex-col gap-2" aria-label={t("title", { period })} data-testid="usage-summary">
      <h2 className="text-sm font-medium text-muted-foreground">{t("title", { period })}</h2>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {tiles.map(([key, label, value]) => (
          <Card key={key} className="flex flex-col gap-1 p-3" data-testid={`usage-${key}`}>
            <span className="text-xs text-muted-foreground">{label}</span>
            <span className="text-lg font-semibold tabular-nums">{u.isPending ? "…" : value}</span>
          </Card>
        ))}
      </div>
      {total.unpriced > 0 && (
        <p className="text-sm text-warning" role="status" data-testid="usage-unpriced">
          {t("unpriced", { count: total.unpriced })}
        </p>
      )}
    </section>
  );
}

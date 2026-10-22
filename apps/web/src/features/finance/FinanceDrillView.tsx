"use client";
import * as React from "react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { ArrowDownRight, ArrowLeft, ArrowRight, ArrowUpRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Sparkline } from "@/components/Sparkline";
import { StatusBadge } from "@/components/StatusBadge";
import { PeriodPicker } from "@/features/dashboard/PeriodPicker";
import { usePeriod } from "@/features/dashboard/period";
import { formatMoneyShort, formatNumber, formatPct, type AppLocale } from "@/lib/format";
import { cn } from "@/lib/utils";
import { LineageDialog } from "./LineageDialog";
import type { CardDef } from "./drilldown";
import { useFinanceDrilldown, type CardView } from "./use-finance-drilldown";

function display(c: CardView, locale: AppLocale, months: string): string {
  if (c.value === null) return "—";
  if (c.kind === "money") return formatMoneyShort(c.value, locale);
  if (c.kind === "pct") return formatPct(c.value, locale);
  return `${formatNumber(c.value, locale)} ${months}`;
}

function TrendArrow({ c }: { c: CardView }) {
  const t = useTranslations("financeDrill.trend");
  if (!c.trend) return null;
  const good = c.trend === "flat" ? null : (c.trend === "up") === c.upIsGood;
  const Icon = c.trend === "up" ? ArrowUpRight : c.trend === "down" ? ArrowDownRight : ArrowRight;
  return (
    <span className={cn("flex items-center gap-0.5 text-xs", good === null ? "text-muted-foreground" : good ? "text-success" : "text-danger")} data-testid="trend" data-trend={c.trend}>
      <Icon className="h-4 w-4" aria-hidden />{t(c.trend)}
    </span>
  );
}

/** SCR-03 lite (T-511): Trụ Tài chính — 6 metric cards + 3-level lineage modal. */
export function FinanceDrillView() {
  const t = useTranslations();
  const locale = useLocale() as AppLocale;
  const { period, withPeriod } = usePeriod();
  const view = useFinanceDrilldown(period);
  const [open, setOpen] = React.useState<CardDef | null>(null);

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-4" data-testid="pillar-detail" data-pillar="F">
      <Link href={withPeriod("/dashboard")} className="flex items-center gap-1 text-sm text-primary"><ArrowLeft className="h-4 w-4" aria-hidden />{t("buttons.back")}</Link>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-semibold">{t("financeDrill.title")}</h1>
          {view.status && <StatusBadge status={view.status} />}
        </div>
        <PeriodPicker />
      </div>
      {view.error ? (
        <Card className="flex items-center justify-between gap-3 p-4 text-sm">
          {t("dashboard.unavailable")}
          <Button variant="outline" size="sm" onClick={view.refetch}>{t("buttons.retry")}</Button>
        </Card>
      ) : (
        <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3" data-testid="finance-cards">
          {view.cards.map((c) =>
            view.loading ? (
              <Card key={c.key} className="h-40 animate-pulse bg-muted" aria-busy="true" />
            ) : (
              <button
                key={c.key}
                type="button"
                onClick={() => setOpen(c)}
                className="rounded-lg text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                data-testid={`fin-card-${c.key}`}
                aria-label={t("financeDrill.openLineage", { metric: t(`financeDrill.card.${c.key}`) })}
              >
                <Card className="flex h-full flex-col gap-2 p-4 transition-shadow hover:shadow-md" data-testid="fin-card">
                  <div className="flex items-start justify-between gap-2">
                    <h2 className="text-sm font-medium text-muted-foreground">{t(`financeDrill.card.${c.key}`)}</h2>
                    {c.status && <StatusBadge status={c.status} />}
                  </div>
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="text-2xl font-semibold tabular-nums" data-testid="fin-value">{display(c, locale, t("financeDrill.months"))}</span>
                    <TrendArrow c={c} />
                  </div>
                  {c.series.length >= 2 ? (
                    <Sparkline values={c.series} label={t("financeDrill.sparkline", { metric: t(`financeDrill.card.${c.key}`) })} />
                  ) : (
                    <p className="h-10 text-xs text-muted-foreground">{t(`financeDrill.hint.${c.key}` as "financeDrill.hint.budget")}</p>
                  )}
                </Card>
              </button>
            ),
          )}
        </section>
      )}
      <LineageDialog card={open} month={view.month} onClose={() => setOpen(null)} />
    </div>
  );
}

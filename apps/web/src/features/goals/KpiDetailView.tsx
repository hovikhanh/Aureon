"use client";
/**
 * SCR-58 `/goals/kpis/[id]` (T-627F, 06 §3.4): tabs Tổng quan (status card + chart + targets per
 * period with closed versions "đổi ngày dd/MM/yyyy — lý do") · Liên kết · Lịch sử · Tài liệu gốc ·
 * Hoạt động AI (placeholder). "Ghi số đo" / "Đặt target kỳ" (not EMP) disabled when the period is locked.
 */
import * as React from "react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { ApiError } from "@/lib/api-client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { formatDate, formatPct, formatPeriod, type AppLocale } from "@/lib/format";
import { businessToday } from "@/lib/work-dates";
import { BandChip, LoadError, useGoalError } from "./common";
import { KpiChart } from "./KpiChart";
import { MeasureDialog, TargetDialog } from "./KpiDialogs";
import { KpiHistory, KpiLinks } from "./KpiTabs";
import { formatValue, periodKeyOf } from "./logic";
import { useKpi, useKpiEvaluations, useKpiTargets, type KpiOut, type KpiTargetOut } from "./use-goals";
import type { GoalCaps } from "./GoalsShell";

const TABS = ["overview", "links", "history", "sources", "ai"] as const;
type Tab = (typeof TABS)[number];

export function KpiDetailView({ id, caps }: { id: string; caps: GoalCaps }) {
  const t = useTranslations("goals");
  const errText = useGoalError();
  const kpi = useKpi(id);
  const [tab, setTab] = React.useState<Tab>("overview");
  if (kpi.isError) {
    const e = kpi.error;
    if (e instanceof ApiError && (e.status === 403 || e.status === 404)) return <p role="alert" className="text-sm text-danger" data-testid="kpi-denied">{errText(e)}</p>;
    return <LoadError onRetry={() => void kpi.refetch()} />;
  }
  if (kpi.isPending) return <div className="h-40 animate-pulse rounded bg-muted" />;
  const k = kpi.data;
  return (
    <section className="flex flex-col gap-4" data-testid="kpi-detail" data-scr="SCR-58">
      <Link href="/goals" className="text-sm text-primary hover:underline">← {t("kpi.back")}</Link>
      <Header k={k} caps={caps} />
      <div role="tablist" aria-label={k.name} className="flex flex-wrap gap-1 border-b">
        {TABS.map((x) => (
          <button key={x} role="tab" type="button" aria-selected={tab === x} onClick={() => setTab(x)} data-testid={`kpi-tab-${x}`}
            className={`-mb-px border-b-2 px-3 py-2 text-sm ${tab === x ? "border-primary font-medium text-primary" : "border-transparent text-muted-foreground"}`}>
            {t(`kpi.tabs.${x}`)}
          </button>
        ))}
      </div>
      <div role="tabpanel">
        {tab === "overview" && <Overview k={k} />}
        {tab === "links" && <KpiLinks k={k} />}
        {tab === "history" && <KpiHistory id={k.id} unit={k.unit} />}
        {tab === "sources" && <p className="text-sm text-muted-foreground" data-testid="kpi-sources">{t("kpi.noSources")}</p>}
        {tab === "ai" && <p className="text-sm text-muted-foreground" data-testid="kpi-ai">{t("kpi.aiPlaceholder")}</p>}
      </div>
    </section>
  );
}

function Header({ k, caps }: { k: KpiOut; caps: GoalCaps }) {
  const t = useTranslations("goals");
  const targets = useKpiTargets(k.id);
  const period = periodKeyOf(k.period_type, businessToday());
  const locked = (targets.data ?? []).some((x) => x.period_key === period && x.valid_to === null && x.locked_at !== null);
  const [open, setOpen] = React.useState<"measure" | "target" | null>(null);
  const canMeasure = caps.canManage || k.owner_id === caps.userId;
  const action = (key: "measure" | "setTarget", dlg: "measure" | "target") => (
    <Tooltip>
      <TooltipTrigger asChild>
        <span><Button size="sm" variant={dlg === "measure" ? "default" : "outline"} disabled={locked} onClick={() => setOpen(dlg)} data-testid={`kpi-${key}`}>{t(`kpi.${key}`)}</Button></span>
      </TooltipTrigger>
      {locked && <TooltipContent>{t("kpi.lockedHint")}</TooltipContent>}
    </Tooltip>
  );
  return (
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 className="text-xl font-semibold">{k.code} · {k.name}</h1>
        <p className="text-sm text-muted-foreground">{t(`kpi.periodType.${k.period_type}` as "kpi.periodType.MONTH")} · {t(`kpi.direction.${k.direction}` as "kpi.direction.HIGHER_IS_BETTER")}</p>
      </div>
      <TooltipProvider>
        <div className="flex gap-2">
          {canMeasure && action("measure", "measure")}
          {caps.canManage && action("setTarget", "target")}
        </div>
      </TooltipProvider>
      <MeasureDialog open={open === "measure"} onOpenChange={(o) => setOpen(o ? "measure" : null)} kpiId={k.id} period={period} />
      <TargetDialog open={open === "target"} onOpenChange={(o) => setOpen(o ? "target" : null)} kpiId={k.id} period={period} />
    </div>
  );
}

function Overview({ k }: { k: KpiOut }) {
  const t = useTranslations("goals");
  const locale = useLocale() as AppLocale;
  const evals = useKpiEvaluations(k.id);
  const e = k.latest_evaluation;
  const last = evals.data?.at(-1);
  return (
    <div className="flex flex-col gap-4">
      <div className="rounded border p-4" data-testid="kpi-status">
        {e ? (
          <div className="flex flex-wrap items-center gap-4 text-sm">
            <span className="font-medium">{t("kpi.status", { period: formatPeriod(e.period_key, locale) })}</span>
            <BandChip band={e.band} />
            <span>{t("kpi.actual")}: <b className="tabular-nums">{formatValue(e.actual_value, k.unit, locale)}</b></span>
            <span>{t("kpi.target")}: <b className="tabular-nums">{formatValue(e.target, k.unit, locale)}</b></span>
            <span className="tabular-nums" data-testid="kpi-achievement">{t("kpi.achievement", { value: formatPct(e.achievement_pct, locale) })}</span>
            {last && <span className="tabular-nums">{t("kpi.gap")}: {formatValue(last.gap_value, k.unit, locale)}</span>}
            {e.previous_band && <span className="text-muted-foreground">{t("kpi.previousBand", { band: t(`band.${e.previous_band}`) })}</span>}
            {last && <Badge variant={last.measured_on_time ? "success" : "warning"}>{last.measured_on_time ? t("kpi.onTime") : t("kpi.late")}</Badge>}
          </div>
        ) : <p className="text-sm text-muted-foreground">{t("tree.noEvaluation")}</p>}
      </div>
      <div className="rounded border p-4">
        <h2 className="mb-2 text-sm font-semibold">{t("kpi.chart")}</h2>
        {evals.isError ? <LoadError onRetry={() => void evals.refetch()} /> : evals.isPending ? <div className="h-64 animate-pulse rounded bg-muted" /> :
          <KpiChart evaluations={evals.data} direction={k.direction} unit={k.unit} />}
      </div>
      <Targets k={k} />
    </div>
  );
}

function Targets({ k }: { k: KpiOut }) {
  const t = useTranslations("goals.kpi");
  const locale = useLocale() as AppLocale;
  const targets = useKpiTargets(k.id);
  if (targets.isError) return <LoadError onRetry={() => void targets.refetch()} />;
  const byPeriod = new Map<string, KpiTargetOut[]>();
  for (const x of targets.data ?? []) byPeriod.set(x.period_key, [...(byPeriod.get(x.period_key) ?? []), x]);
  return (
    <div className="rounded border p-4" data-testid="kpi-targets">
      <h2 className="mb-2 text-sm font-semibold">{t("targets")}</h2>
      <table className="w-full text-sm">
        <thead><tr className="text-left text-muted-foreground"><th className="py-1">{t("period")}</th><th>{t("target")}</th><th>{t("validFrom")}</th></tr></thead>
        <tbody>
          {[...byPeriod.entries()].sort(([a], [b]) => b.localeCompare(a)).map(([p, rows]) => rows.map((x) => (
            <tr key={x.id} className={x.valid_to ? "text-muted-foreground line-through decoration-muted-foreground/40" : ""} data-testid={x.valid_to ? "target-closed" : "target-open"}>
              <td className="py-1">{formatPeriod(p, locale)}</td>
              <td className="tabular-nums">{formatValue(x.target, k.unit, locale)}{x.locked_at && <Badge variant="outline" className="ml-2">{t("locked")}</Badge>}</td>
              <td>
                {formatDate(x.valid_from, locale)}
                {x.valid_to && <span className="ml-2 no-underline" data-testid="target-change">{t("targetChanged", { date: formatDate(x.valid_to, locale), reason: rows.find((r) => r.valid_from === x.valid_to)?.reason ?? t("noReason") })}</span>}
              </td>
            </tr>
          )))}
        </tbody>
      </table>
    </div>
  );
}

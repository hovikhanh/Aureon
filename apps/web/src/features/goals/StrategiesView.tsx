"use client";
/** `/goals/strategies` (F12): Strategy list (EP-STR-02) + its Strategic Objectives (EP-STR-07), with create where the role may write. */
import * as React from "react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { ArrowLeft } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { formatDate, type AppLocale } from "@/lib/format";
import { codeLabel } from "@/lib/humanize";
import type { GoalCaps } from "./GoalsShell";
import { StrategicObjectiveDialog, StrategyDialog } from "./StrategyEditors";
import { LoadError } from "./common";
import { useStrategicObjectives, useStrategies } from "./use-goals";

export function StrategiesView({ caps }: { caps: GoalCaps }) {
  const t = useTranslations("goals");
  const tAll = useTranslations();
  const locale = useLocale() as AppLocale;
  const list = useStrategies();
  const [chosen, setChosen] = React.useState<string | null>(null);
  const [dialog, setDialog] = React.useState<"strategy" | "so" | null>(null);
  const rows = list.data ?? [];
  const active = rows.find((s) => s.id === chosen) ?? rows.find((s) => s.status === "active") ?? rows[0] ?? null;
  const sos = useStrategicObjectives(active?.id ?? null);
  const status = (s: string) => codeLabel(tAll as never, "goals.editor.status", s);
  return (
    <section className="flex flex-col gap-4" data-testid="strategies">
      <Link href="/goals" className="flex items-center gap-1 text-sm text-primary hover:underline"><ArrowLeft className="h-4 w-4" aria-hidden />{t("tree.title")}</Link>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h1 className="text-xl font-semibold">{t("strategy.title")}</h1>
        {caps.canWriteStrategy && <Button size="sm" variant="outline" onClick={() => setDialog("strategy")} data-testid="strategy-create">{t("strategy.create")}</Button>}
      </div>
      {list.isError && <LoadError onRetry={() => void list.refetch()} />}
      {list.isPending && <div className="h-32 animate-pulse rounded bg-muted" />}
      {list.isSuccess && rows.length === 0 && <p className="text-sm text-muted-foreground" data-testid="strategies-empty">{t("strategy.empty")}</p>}
      {rows.length > 0 && (
        <ul className="grid gap-3 md:grid-cols-2" data-testid="strategy-list">
          {rows.map((s) => (
            <li key={s.id}>
              <button type="button" onClick={() => setChosen(s.id)} aria-pressed={s.id === active?.id} data-testid="strategy-row" data-code={s.code}
                className={`flex h-full w-full flex-col gap-1 rounded-lg border bg-card p-4 text-left hover:bg-muted ${s.id === active?.id ? "border-primary" : ""}`}>
                <span className="flex flex-wrap items-center gap-2 font-medium">{s.name}<Badge variant={s.status === "active" ? "primary" : "outline"}>{status(s.status)}</Badge></span>
                <span className="text-sm text-muted-foreground tabular-nums">{s.code} · {formatDate(s.period_start, locale)} – {formatDate(s.period_end, locale)}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {active && (
        <Card className="flex flex-col gap-3 p-4" data-testid="strategy-objectives">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-sm font-semibold">{t("strategy.soTitle", { name: active.name })}</h2>
            {caps.canWriteSo && <Button size="sm" variant="outline" onClick={() => setDialog("so")} data-testid="so-create">{t("strategy.createSo")}</Button>}
          </div>
          {sos.isError && <LoadError onRetry={() => void sos.refetch()} />}
          {sos.isSuccess && sos.data.length === 0 && <p className="text-sm text-muted-foreground" data-testid="so-empty">{t("strategy.soEmpty")}</p>}
          {sos.isSuccess && sos.data.length > 0 && (
            <ul className="flex flex-col divide-y text-sm">
              {sos.data.map((o) => (
                <li key={o.id} className="flex flex-wrap items-center gap-2 py-2" data-testid="so-row">
                  <span className="text-muted-foreground">{o.code}</span>
                  <span className="font-medium">{o.title}</span>
                  {o.pillar && <Badge variant="outline">{codeLabel(tAll as never, "goals.pillar", o.pillar)}</Badge>}
                </li>
              ))}
            </ul>
          )}
        </Card>
      )}
      {caps.canWriteStrategy && <StrategyDialog open={dialog === "strategy"} onOpenChange={(o) => setDialog(o ? "strategy" : null)} caps={caps} />}
      {caps.canWriteSo && active && <StrategicObjectiveDialog open={dialog === "so"} onOpenChange={(o) => setDialog(o ? "so" : null)} caps={caps} strategy={active} />}
    </section>
  );
}

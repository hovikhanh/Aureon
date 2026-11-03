"use client";
/**
 * SCR-59 `/goals/objectives/[id]` (T-627F, 06 §3.4): Objective header + KR list (progress,
 * ConfidenceBadge, at-risk + reasons, "check-in gần nhất x ngày trước"); `?kr=` selects a KR →
 * check-in history panel (EP-PRF-01) + sparkline of `kr_measurement.progress_pct`.
 */
import * as React from "react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { ApiError } from "@/lib/api-client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Sparkline } from "@/components/Sparkline";
import { formatDate, formatDateTime, formatPct, formatPeriod, type AppLocale } from "@/lib/format";
import { businessToday } from "@/lib/work-dates";
import { AtRiskFlag, KrConfidence, LoadError, Progress, useGoalError } from "./common";
import { ArchiveDialog, KeyResultEditorDialog, ObjectiveEditorDialog } from "./GoalEditors";
import { daysAgo, formatValue } from "./logic";
import { useKrCheckIns, useObjective, useObjectiveKrs, type KeyResultOut } from "./use-goals";
import type { GoalCaps } from "./GoalsShell";

export function ObjectiveDetailView({ id, caps }: { id: string; caps: GoalCaps }) {
  const t = useTranslations("goals");
  const locale = useLocale() as AppLocale;
  const errText = useGoalError();
  const sp = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const obj = useObjective(id);
  const krs = useObjectiveKrs(id);
  const selected = sp.get("kr");
  // one editor at a time: objective edit/archive, add KR, or edit/archive one KR (`kr:<mode>:<id>`)
  const [dlg, setDlg] = React.useState<string | null>(null);
  const close = (o: boolean) => { if (!o) setDlg(null); };
  if (obj.isError) {
    const e = obj.error;
    if (e instanceof ApiError && (e.status === 403 || e.status === 404)) return <p role="alert" className="text-sm text-danger" data-testid="objective-denied">{errText(e)}</p>;
    return <LoadError onRetry={() => void obj.refetch()} />;
  }
  if (obj.isPending) return <div className="h-40 animate-pulse rounded bg-muted" />;
  const o = obj.data;
  const select = (kr: string) => router.replace(`${pathname}?kr=${kr}`, { scroll: false });
  const current = (krs.data ?? []).find((k) => k.id === selected) ?? null;
  return (
    <section className="flex flex-col gap-4" data-testid="objective-detail" data-scr="SCR-59">
      <Link href="/goals" className="text-sm text-primary hover:underline">← {t("objective.back")}</Link>
      <header className="flex flex-col gap-2">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <h1 className="text-xl font-semibold">{o.title}</h1>
          {caps.canManage && (
            <div className="flex gap-2">
              <Button size="sm" variant="outline" onClick={() => setDlg("objective:edit")} data-testid="objective-edit">{t("editor.edit")}</Button>
              <Button size="sm" variant="ghost" className="text-danger" onClick={() => setDlg("objective:archive")} data-testid="objective-archive">{t("editor.archiveAction")}</Button>
            </div>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <Badge variant="outline">{t("objective.period", { period: formatPeriod(o.period_key, locale) })}</Badge>
          <Badge variant="outline">{t(`objective.level.${o.level}` as "objective.level.company")}</Badge>
          <Badge>{t(`objective.status.${o.status}` as "objective.status.active")}</Badge>
          <Progress value={o.progress_pct} label={t("objective.progress")} />
          <span className="tabular-nums" data-testid="objective-progress">{formatPct(o.progress_pct, locale)}</span>
          {(o.at_risk_kr_count ?? 0) > 0 && <Badge variant="danger">{t("tree.atRiskCount", { count: o.at_risk_kr_count ?? 0 })}</Badge>}
        </div>
      </header>
      <div className="grid gap-4 lg:grid-cols-[1fr_24rem]">
        <div className="rounded border">
          <div className="flex items-center justify-between gap-2 border-b p-3">
            <h2 className="text-sm font-semibold">{t("objective.krs")}</h2>
            {caps.canManage && <Button size="sm" variant="outline" onClick={() => setDlg("kr:create")} data-testid="kr-add">{t("editor.createKr")}</Button>}
          </div>
          {krs.isError ? <LoadError onRetry={() => void krs.refetch()} /> : (
            <ul className="divide-y" data-testid="objective-krs">
              {(krs.data ?? []).map((k) => (
                <KrItem key={k.id} k={k} selected={k.id === selected} onSelect={() => select(k.id)} mine={k.owner_id === caps.userId}
                  onEdit={caps.canManage ? () => setDlg(`kr:edit:${k.id}`) : undefined} onArchive={caps.canManage ? () => setDlg(`kr:archive:${k.id}`) : undefined} />
              ))}
            </ul>
          )}
        </div>
        <KrHistory kr={current} />
      </div>
      {caps.canManage && (() => {
        const [kind, mode, krId] = (dlg ?? "").split(":");
        const target = (krs.data ?? []).find((k) => k.id === krId);
        return (
          <>
            <ObjectiveEditorDialog open={dlg === "objective:edit"} onOpenChange={close} caps={caps} objective={o} defaultPeriod={o.period_key} />
            <ArchiveDialog open={dlg === "objective:archive"} onOpenChange={close} kind="objective" id={o.id} name={o.title} after="/goals" />
            <KeyResultEditorDialog open={dlg === "kr:create" || (kind === "kr" && mode === "edit" && Boolean(target))} onOpenChange={close} caps={caps} objectiveId={o.id}
              kr={mode === "edit" ? target : undefined} />
            {target && <ArchiveDialog open={kind === "kr" && mode === "archive"} onOpenChange={close} kind="kr" id={target.id} name={target.title} />}
          </>
        );
      })()}
    </section>
  );
}

function KrItem({ k, selected, onSelect, mine, onEdit, onArchive }: {
  k: KeyResultOut; selected: boolean; onSelect: () => void; mine: boolean; onEdit?: () => void; onArchive?: () => void;
}) {
  const t = useTranslations("goals");
  const locale = useLocale() as AppLocale;
  const today = businessToday();
  const days = k.last_checked_in_at ? daysAgo(k.last_checked_in_at, today) : null;
  return (
    <li className={`flex flex-col gap-1 p-3 ${selected ? "bg-muted" : ""}`} data-testid={`kr-item-${k.id}`} data-at-risk={k.at_risk ? "true" : "false"}>
      <button type="button" onClick={onSelect} className="text-left font-medium hover:underline" aria-pressed={selected} data-testid={`kr-select-${k.id}`}>{k.title}</button>
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <Progress value={k.progress_pct} label={t("objective.progress")} />
        <span className="tabular-nums">{formatPct(k.progress_pct, locale)}</span>
        <span className="tabular-nums text-muted-foreground">
          {t("objective.baseline")} {formatValue(k.baseline, k.unit, locale)} · {t("objective.current")} {formatValue(k.current_value, k.unit, locale)} · {t("objective.target")} {formatValue(k.target, k.unit, locale)}
        </span>
        <KrConfidence value={k.confidence} />
        {k.at_risk && <AtRiskFlag />}
        {mine && <Link href="/goals/check-ins" className="text-xs text-primary hover:underline">{t("tree.checkIn")}</Link>}
        {onEdit && <button type="button" className="text-xs text-primary hover:underline" onClick={onEdit} data-testid={`kr-edit-${k.id}`}>{t("editor.edit")}</button>}
        {onArchive && <button type="button" className="text-xs text-danger hover:underline" onClick={onArchive} data-testid={`kr-archive-${k.id}`}>{t("editor.archiveAction")}</button>}
      </div>
      {k.at_risk && (
        <ul className="flex flex-wrap gap-2 text-xs text-danger" data-testid="at-risk-reasons">
          {k.at_risk_since && <li>{t("atRisk.since", { date: formatDate(k.at_risk_since, locale) })}</li>}
          {(k.at_risk_reasons ?? []).map((r) => <li key={r} data-reason={r}>• {t(`atRisk.reasons.${r}`)}</li>)}
        </ul>
      )}
      <p className="text-xs text-muted-foreground" data-testid="kr-last-checkin">
        {days === null ? t("objective.neverCheckedIn") : days === 0 ? t("objective.lastCheckInToday") : t("objective.lastCheckIn", { days })}
      </p>
    </li>
  );
}

function KrHistory({ kr }: { kr: KeyResultOut | null }) {
  const t = useTranslations("goals");
  const locale = useLocale() as AppLocale;
  const h = useKrCheckIns(kr?.id ?? null);
  return (
    <aside className="rounded border p-3" data-testid="kr-history" aria-live="polite">
      <h2 className="mb-2 text-sm font-semibold">{t("objective.history")}</h2>
      {!kr ? <p className="text-sm text-muted-foreground">{t("objective.selectKr")}</p> : h.isError ? <LoadError onRetry={() => void h.refetch()} /> : h.isPending ? <div className="h-24 animate-pulse rounded bg-muted" /> : (
        <div className="flex flex-col gap-3">
          <p className="text-sm font-medium">{kr.title}</p>
          {h.data.length > 1 && (
            <div data-testid="kr-sparkline">
              <Sparkline values={[...h.data].reverse().map((c) => c.kr_measurement?.progress_pct ?? 0)} label={`${t("objective.progress")} — ${kr.title}`} />
            </div>
          )}
          {h.data.length === 0 ? <p className="text-sm text-muted-foreground">{t("objective.noHistory")}</p> : (
            <ol className="flex flex-col gap-2 text-sm" data-testid="kr-history-list">
              {h.data.map((c) => (
                <li key={c.id} className="flex flex-col gap-0.5 border-l-2 pl-2" data-testid="kr-history-row">
                  <span className="flex flex-wrap items-center gap-2">
                    <span className="tabular-nums font-medium">{formatValue(Number(c.value), kr.unit, locale)}</span>
                    {c.kr_measurement && <span className="tabular-nums text-muted-foreground">{formatPct(c.kr_measurement.progress_pct, locale)}</span>}
                    <KrConfidence value={c.confidence} />
                  </span>
                  <span className="text-xs text-muted-foreground">{formatDateTime(c.checked_in_at, locale)}</span>
                  {c.note && <span>{c.note}</span>}
                  {c.blocker && <span className="text-danger">{t("objective.blocker")}: {c.blocker}</span>}
                </li>
              ))}
            </ol>
          )}
        </div>
      )}
    </aside>
  );
}

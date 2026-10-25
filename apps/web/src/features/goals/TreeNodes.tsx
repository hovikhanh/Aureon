"use client";
/** Row components of the SCR-41 tree (KPI · Objective/KR · Initiative). Restricted nodes are plain text, not links (R-DEC-57). */
import * as React from "react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import type { Api } from "@aureon/shared-types";
import { Badge } from "@/components/ui/badge";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { formatPct, formatPeriod, type AppLocale } from "@/lib/format";
import { AtRiskFlag, BandChip, KrConfidence, Progress } from "./common";
import { formatValue, type KpiNode, type KrNode, type ObjNode } from "./logic";

export function Toggle({ name, open, children, testId }: { name: string; open?: boolean; children: React.ReactNode; testId?: string }) {
  const t = useTranslations("goals.tree");
  const [isOpen, setOpen] = React.useState(open ?? true);
  return (
    <Collapsible open={isOpen} onOpenChange={setOpen} data-testid={testId}>
      <CollapsibleTrigger className="mr-1 inline-flex size-5 items-center justify-center rounded text-muted-foreground hover:bg-muted" aria-label={t("expand", { name })}>
        <span aria-hidden>{isOpen ? "▾" : "▸"}</span>
      </CollapsibleTrigger>
      {children}
    </Collapsible>
  );
}
export { CollapsibleContent as ToggleContent };

function Restricted({ label, testId }: { label: string; testId: string }) {
  const t = useTranslations("goals.tree");
  return (
    <span className="text-muted-foreground" title={t("restrictedHint")} data-testid={testId} data-restricted="true">
      {label} <Badge variant="outline">{t("restricted")}</Badge>
    </span>
  );
}

export function KpiRow({ k, depth = 0 }: { k: KpiNode; depth?: number }) {
  const locale = useLocale() as AppLocale;
  const t = useTranslations("goals");
  const e = k.latest_evaluation;
  const label = `${k.code ?? ""} ${k.name ?? ""}`.trim();
  return (
    <li className="flex flex-col gap-1" style={{ paddingLeft: depth * 16 }} data-testid={`kpi-node-${k.code ?? k.id}`}>
      <div className="flex flex-wrap items-center gap-2 text-sm">
        {k.restricted ? <Restricted label={label} testId={`kpi-restricted-${k.id}`} /> : (
          <>
            <Link href={`/goals/kpis/${k.id}`} className="font-medium hover:underline">{label}</Link>
            <BandChip band={e?.band} />
            {e && (
              <span className="tabular-nums text-muted-foreground">
                {formatValue(e.actual_value, k.unit ?? "", locale)} / {formatValue(e.target, k.unit ?? "", locale)} · {formatPct(e.achievement_pct, locale)} · {formatPeriod(e.period_key, locale)}
              </span>
            )}
            {!e && <span className="sr-only">{t("tree.noEvaluation")}</span>}
          </>
        )}
      </div>
      {(k.children ?? []).length > 0 && <ul className="flex flex-col gap-1">{k.children!.map((c) => <KpiRow key={c.id} k={c} depth={depth + 1} />)}</ul>}
    </li>
  );
}

export function KrRow({ kr, objectiveId, mine }: { kr: KrNode; objectiveId: string; mine: boolean }) {
  const locale = useLocale() as AppLocale;
  const t = useTranslations("goals");
  return (
    <li className="flex flex-wrap items-center gap-2 pl-6 text-sm" data-testid={`kr-node-${kr.id}`} data-at-risk={kr.at_risk ? "true" : "false"}>
      <Link href={`/goals/objectives/${objectiveId}?kr=${kr.id}`} className="hover:underline">{kr.title}</Link>
      <Progress value={kr.progress_pct} label={t("tree.progress", { value: formatPct(kr.progress_pct, locale) })} />
      <span className="tabular-nums text-muted-foreground">
        {formatValue(kr.current_value, kr.unit, locale)} / {formatValue(kr.target, kr.unit, locale)} · {formatPct(kr.progress_pct, locale)}
      </span>
      <KrConfidence value={kr.confidence} />
      {kr.at_risk && <AtRiskFlag />}
      {mine && <Link href="/goals/check-ins" className="text-xs text-primary hover:underline" data-testid={`kr-checkin-${kr.id}`}>{t("tree.checkIn")}</Link>}
    </li>
  );
}

export function ObjRow({ o, userId, depth = 0 }: { o: ObjNode; userId: string; depth?: number }) {
  const locale = useLocale() as AppLocale;
  const t = useTranslations("goals");
  const title = o.title ?? "";
  return (
    <li className="flex flex-col gap-1" style={{ paddingLeft: depth * 16 }} data-testid={`obj-node-${o.id}`}>
      <div className="flex flex-wrap items-center gap-2 text-sm">
        {o.restricted ? <Restricted label={title} testId={`obj-restricted-${o.id}`} /> : (
          <>
            <Link href={`/goals/objectives/${o.id}`} className="font-medium hover:underline">{title}</Link>
            {o.period_key && <Badge variant="outline">{formatPeriod(o.period_key, locale)}</Badge>}
            <Progress value={o.progress_pct ?? 0} label={t("tree.progress", { value: formatPct(o.progress_pct ?? 0, locale) })} />
            <span className="tabular-nums text-muted-foreground">{formatPct(o.progress_pct ?? 0, locale)}</span>
            {(o.at_risk_kr_count ?? 0) > 0 && <Badge variant="danger">{t("tree.atRiskCount", { count: o.at_risk_kr_count ?? 0 })}</Badge>}
          </>
        )}
      </div>
      <ul className="flex flex-col gap-1">{(o.key_results ?? []).map((kr) => <KrRow key={kr.id} kr={kr} objectiveId={o.id} mine={kr.owner_id === userId} />)}</ul>
      {(o.children ?? []).length > 0 && <ul className="flex flex-col gap-1">{o.children!.map((c) => <ObjRow key={c.id} o={c} userId={userId} depth={depth + 1} />)}</ul>}
    </li>
  );
}

export function IniRow({ i }: { i: Api.IniNode }) {
  const locale = useLocale() as AppLocale;
  const t = useTranslations("goals.tree");
  return (
    <li className="flex flex-col gap-1 text-sm" data-testid={`ini-node-${i.code ?? i.id}`}>
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-medium">{i.code} {i.title}</span>
        <Progress value={i.progress_pct ?? 0} label={t("progress", { value: formatPct(i.progress_pct ?? 0, locale) })} />
        <span className="tabular-nums text-muted-foreground">{formatPct(i.progress_pct ?? 0, locale)}</span>
        {i.on_track !== null && i.on_track !== undefined && (
          <Badge variant={i.on_track ? "success" : "danger"} data-testid="on-track">{i.on_track ? t("onTrack") : t("late")}</Badge>
        )}
      </div>
      {(i.projects ?? []).length > 0 && (
        <ul className="flex flex-wrap gap-2 pl-6">
          {i.projects!.map((p) => <li key={p.id}><Link href={`/work/projects/${p.id}`} className="text-xs text-primary hover:underline" data-testid={`ini-project-${p.code}`}>{p.code} · {p.name}</Link></li>)}
        </ul>
      )}
    </li>
  );
}

"use client";
/**
 * SCR-41 `/goals` (T-626F, 06 §3.4): Strategy selector · OKR period (default current quarter) ·
 * department filter (CEO/DIR) · "at-risk / dưới ngưỡng" quick filter · collapsible tree SO →
 * KPI / OKR→KR / Initiative→Project · "Chưa gắn chiến lược" last. Filters live in the URL.
 */
import * as React from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/select";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { useDepartments } from "@/features/admin/org/use-org";
import { formatPct, formatPeriod, type AppLocale } from "@/lib/format";
import { businessToday } from "@/lib/work-dates";
import { LoadError, Progress } from "./common";
import { filterKpis, filterObjs, periodKeyOf, soVisible, type SONode } from "./logic";
import { IniRow, KpiRow, ObjRow, Toggle, ToggleContent } from "./TreeNodes";
import { useGoalTree, useStrategies } from "./use-goals";
import type { GoalCaps } from "./GoalsShell";

/** Current quarter ± 2 (06 §3.4: period selector). */
function quarterOptions(today: string): string[] {
  const y = Number(today.slice(0, 4));
  const q = Number(periodKeyOf("QUARTER", today).slice(-1));
  const out: string[] = [];
  for (let d = -2; d <= 2; d++) {
    const idx = y * 4 + (q - 1) + d;
    out.push(`${Math.floor(idx / 4)}-Q${(idx % 4) + 1}`);
  }
  return out;
}

export function GoalTreeView({ caps }: { caps: GoalCaps }) {
  const t = useTranslations("goals");
  const locale = useLocale() as AppLocale;
  const router = useRouter();
  const pathname = usePathname();
  const sp = useSearchParams();
  const today = businessToday();
  const period = sp.get("period") ?? periodKeyOf("QUARTER", today);
  const strategyId = sp.get("strategy") ?? "";
  const dept = sp.get("department") ?? "";
  const flagged = sp.get("flagged") === "1";
  const set = (k: string, v: string) => {
    const next = new URLSearchParams(sp.toString());
    if (v) next.set(k, v); else next.delete(k);
    router.replace(`${pathname}?${next.toString()}`, { scroll: false });
  };
  const tree = useGoalTree({ period_key: period, strategy_id: strategyId || undefined, department_id: dept || undefined });
  const strategies = useStrategies();
  const departments = useDepartments();
  const showDept = caps.canFilterDepartment;

  return (
    <section className="flex flex-col gap-4" data-testid="goals-tree" data-scr="SCR-41">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h1 className="text-xl font-semibold">{caps.isEmployee ? t("tree.empSelf") : t("tree.title")}</h1>
        {caps.canManage && (
          <TooltipProvider>
            <div className="flex gap-2">
              {(["createKpi", "createObjective"] as const).map((k) => (
                <Tooltip key={k}>
                  <TooltipTrigger asChild><span><Button size="sm" variant="outline" disabled data-testid={`goals-${k}`}>{t(`tree.${k}`)}</Button></span></TooltipTrigger>
                  <TooltipContent>{t("tree.createSoon")}</TooltipContent>
                </Tooltip>
              ))}
            </div>
          </TooltipProvider>
        )}
      </div>
      <div className="flex flex-wrap items-end gap-3" data-testid="goals-filters">
        {!caps.isEmployee && (
          <div className="flex flex-col gap-1">
            <Label htmlFor="g-strategy">{t("tree.strategy")}</Label>
            <NativeSelect id="g-strategy" value={strategyId} onChange={(e) => set("strategy", e.target.value)} data-testid="goals-strategy">
              {(strategies.data ?? []).filter((s) => s.status === "active").map((s) => <option key={s.id} value="">{s.code} · {s.name}</option>)}
              {(strategies.data ?? []).filter((s) => s.status !== "active").map((s) => <option key={s.id} value={s.id}>{s.code} · {s.name}</option>)}
            </NativeSelect>
          </div>
        )}
        <div className="flex flex-col gap-1">
          <Label htmlFor="g-period">{t("tree.period")}</Label>
          <NativeSelect id="g-period" value={period} onChange={(e) => set("period", e.target.value)} data-testid="goals-period">
            {quarterOptions(today).map((p) => <option key={p} value={p}>{formatPeriod(p, locale)}</option>)}
          </NativeSelect>
        </div>
        {showDept && (
          <div className="flex flex-col gap-1">
            <Label htmlFor="g-dept">{t("tree.department")}</Label>
            <NativeSelect id="g-dept" value={dept} onChange={(e) => set("department", e.target.value)} data-testid="goals-department">
              <option value="">{t("tree.allDepartments")}</option>
              {(departments.data?.data ?? []).map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
            </NativeSelect>
          </div>
        )}
        <label className="flex items-center gap-2 pb-2 text-sm">
          <Checkbox checked={flagged} onCheckedChange={(v) => set("flagged", v === true ? "1" : "")} data-testid="goals-flagged" />
          {t("tree.onlyFlagged")}
        </label>
      </div>
      {tree.isError ? <LoadError onRetry={() => void tree.refetch()} /> : tree.isPending ? <div className="h-40 animate-pulse rounded bg-muted" /> : (
        <TreeBody data={tree.data} flagged={flagged} userId={caps.userId} />
      )}
    </section>
  );
}

function TreeBody({ data, flagged, userId }: { data: NonNullable<ReturnType<typeof useGoalTree>["data"]>; flagged: boolean; userId: string }) {
  const t = useTranslations("goals");
  const sos = (data.strategies ?? []).flatMap((s) => s.strategic_objectives ?? []).filter((so) => soVisible(so, flagged));
  const uk = filterKpis(data.unaligned?.kpis ?? [], flagged);
  const uo = filterObjs(data.unaligned?.objectives ?? [], flagged);
  if (!sos.length && !uk.length && !uo.length) return <p className="text-sm text-muted-foreground" data-testid="goals-empty">{t("empty")}</p>;
  return (
    <div className="flex flex-col gap-3">
      {(data.strategies ?? []).map((st) => (
        <p key={st.id} className="text-sm text-muted-foreground" data-testid="strategy-name">{st.code} · {st.name}</p>
      ))}
      <ul className="flex flex-col gap-3">{sos.map((so) => <SoCard key={so.id} so={so} flagged={flagged} userId={userId} />)}</ul>
      {(uk.length > 0 || uo.length > 0) && (
        <section className="rounded border border-dashed p-3" data-testid="goals-unaligned">
          <h2 className="mb-2 text-sm font-semibold">{t("tree.unaligned")}</h2>
          {uk.length > 0 && <ul className="flex flex-col gap-1">{uk.map((k) => <KpiRow key={k.id} k={k} />)}</ul>}
          {uo.length > 0 && <ul className="mt-2 flex flex-col gap-1">{uo.map((o) => <ObjRow key={o.id} o={o} userId={userId} />)}</ul>}
        </section>
      )}
    </div>
  );
}

function SoCard({ so, flagged, userId }: { so: SONode; flagged: boolean; userId: string }) {
  const t = useTranslations("goals");
  const locale = useLocale() as AppLocale;
  const kpis = filterKpis(so.kpis ?? [], flagged);
  const objs = filterObjs(so.objectives ?? [], flagged);
  const inis = (so.initiatives ?? []).filter((i) => !flagged || i.on_track === false);
  const name = `${so.code ?? ""} ${so.title ?? ""}`.trim();
  return (
    <li className="rounded border p-3" data-testid={`so-node-${so.code ?? so.id}`} data-restricted={so.restricted ? "true" : "false"}>
      <Toggle name={name}>
        <span className="inline-flex flex-wrap items-center gap-2 font-medium">
          {name}
          {so.restricted ? <Badge variant="outline">{t("tree.restricted")}</Badge> : (
            <>
              {so.pillar && <Badge variant="outline">{t(`pillar.${so.pillar}`)}</Badge>}
              <Progress value={so.progress_pct ?? 0} label={t("tree.progress", { value: formatPct(so.progress_pct ?? 0, locale) })} />
              <span className="text-sm tabular-nums text-muted-foreground">{formatPct(so.progress_pct ?? 0, locale)}</span>
            </>
          )}
        </span>
        <ToggleContent className="mt-2 flex flex-col gap-3 pl-6">
          {kpis.length > 0 && <Group title={t("tree.kpis")}>{kpis.map((k) => <KpiRow key={k.id} k={k} />)}</Group>}
          {objs.length > 0 && <Group title={t("tree.objectives")}>{objs.map((o) => <ObjRow key={o.id} o={o} userId={userId} />)}</Group>}
          {inis.length > 0 && <Group title={t("tree.initiatives")}>{inis.map((i) => <IniRow key={i.id} i={i} />)}</Group>}
        </ToggleContent>
      </Toggle>
    </li>
  );
}

function Group({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="mb-1 text-xs font-semibold uppercase text-muted-foreground">{title}</h3>
      <ul className="flex flex-col gap-1">{children}</ul>
    </div>
  );
}

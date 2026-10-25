"use client";
/**
 * SCR-60 `/goals/check-ins` (T-628F, 06 §3.4 F4): EMP = own cards (EP-PRF-06). MGR/DIR/CEO = tabs
 * "Của tôi" + "Team": EP-PRF-05 feed filtered by week / department / confidence + KRs in scope that
 * have no check-in this week (from EP-STR-01 `last_checked_in_at`).
 */
import * as React from "react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/select";
import { useDepartments } from "@/features/admin/org/use-org";
import { formatDate, formatDateTime, type AppLocale } from "@/lib/format";
import { addDays, businessToday } from "@/lib/work-dates";
import { CheckInCard } from "./CheckInCard";
import { KrConfidence, LoadError } from "./common";
import { CONFIDENCES, checkedInThisWeek, formatValue, periodKeyOf, treeKrs, weekRangeOf } from "./logic";
import { useCheckInFeed, useCheckInsDue, useGoalTree } from "./use-goals";
import type { GoalCaps } from "./GoalsShell";

export function CheckInsView({ caps }: { caps: GoalCaps }) {
  const t = useTranslations("goals.checkin");
  const [tab, setTab] = React.useState<"mine" | "team">("mine");
  return (
    <section className="flex flex-col gap-4" data-testid="checkins" data-scr="SCR-60">
      <h1 className="text-xl font-semibold">{t("title")}</h1>
      {!caps.isEmployee && (
        <div role="tablist" aria-label={t("title")} className="flex gap-1 border-b">
          {(["mine", "team"] as const).map((x) => (
            <button key={x} role="tab" type="button" aria-selected={tab === x} onClick={() => setTab(x)} data-testid={`checkins-tab-${x}`}
              className={`-mb-px border-b-2 px-3 py-2 text-sm ${tab === x ? "border-primary font-medium text-primary" : "border-transparent text-muted-foreground"}`}>
              {t(x)}
            </button>
          ))}
        </div>
      )}
      {tab === "mine" || caps.isEmployee ? <MyCards /> : <TeamFeed caps={caps} />}
    </section>
  );
}

function MyCards() {
  const t = useTranslations("goals.checkin");
  const due = useCheckInsDue();
  if (due.isError) return <LoadError onRetry={() => void due.refetch()} />;
  if (due.isPending) return <div className="h-40 animate-pulse rounded bg-muted" />;
  if (!due.data.length) return <p className="text-sm text-muted-foreground" data-testid="checkins-empty">{t("emptyMine")}</p>;
  return <div className="grid gap-4 lg:grid-cols-2" data-testid="checkin-cards">{due.data.map((c) => <CheckInCard key={`${c.target_type}-${c.target_id}`} card={c} />)}</div>;
}

function TeamFeed({ caps }: { caps: GoalCaps }) {
  const t = useTranslations("goals");
  const locale = useLocale() as AppLocale;
  const today = businessToday();
  const [week, setWeek] = React.useState<"this" | "last">("this");
  const [dept, setDept] = React.useState("");
  const [conf, setConf] = React.useState("");
  const range = weekRangeOf(week === "this" ? today : addDays(today, -7));
  const feed = useCheckInFeed({ from: range.from, to: range.to, department_id: dept || undefined, confidence: conf || undefined });
  const tree = useGoalTree({ period_key: periodKeyOf("QUARTER", today), department_id: dept || undefined });
  const departments = useDepartments();
  const missing = treeKrs(tree.data).filter((k) => !checkedInThisWeek(k.last_checked_in_at, today));
  return (
    <div className="flex flex-col gap-4" data-testid="checkins-team">
      <div className="flex flex-wrap items-end gap-3">
        <div className="flex flex-col gap-1">
          <Label htmlFor="cf-week">{t("checkin.week")}</Label>
          <NativeSelect id="cf-week" value={week} onChange={(e) => setWeek(e.target.value as "this" | "last")} data-testid="cf-week">
            <option value="this">{t("checkin.thisWeek")} ({formatDate(weekRangeOf(today).from, locale)})</option>
            <option value="last">{t("checkin.lastWeek")}</option>
          </NativeSelect>
        </div>
        {caps.canFilterDepartment && (
          <div className="flex flex-col gap-1">
            <Label htmlFor="cf-dept">{t("tree.department")}</Label>
            <NativeSelect id="cf-dept" value={dept} onChange={(e) => setDept(e.target.value)} data-testid="cf-department">
              <option value="">{t("tree.allDepartments")}</option>
              {(departments.data?.data ?? []).map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
            </NativeSelect>
          </div>
        )}
        <div className="flex flex-col gap-1">
          <Label htmlFor="cf-conf">{t("checkin.confidence")}</Label>
          <NativeSelect id="cf-conf" value={conf} onChange={(e) => setConf(e.target.value)} data-testid="cf-confidence">
            <option value="">{t("checkin.allConfidence")}</option>
            {CONFIDENCES.map((c) => <option key={c} value={c}>{t(`confidence.${c}`)}</option>)}
          </NativeSelect>
        </div>
      </div>
      {feed.isError ? <LoadError onRetry={() => void feed.refetch()} /> : feed.isPending ? <div className="h-32 animate-pulse rounded bg-muted" /> :
        feed.data.length === 0 ? <p className="text-sm text-muted-foreground" data-testid="feed-empty">{t("checkin.feedEmpty")}</p> : (
          <ul className="flex flex-col divide-y rounded border" data-testid="checkin-feed">
            {feed.data.map((c) => (
              <li key={c.id} className="flex flex-wrap items-center gap-2 p-3 text-sm" data-testid="feed-row" data-confidence={c.confidence}>
                <Badge variant="outline">{c.target_type === "kpi" ? t("checkin.kpi") : t("checkin.kr")}</Badge>
                <span className="font-medium">{c.target_title}</span>
                <span className="tabular-nums">{formatValue(Number(c.value), null, locale)}</span>
                <KrConfidence value={c.confidence} />
                <span className="text-muted-foreground">{formatDateTime(c.checked_in_at, locale)}</span>
                {c.blocker && <span className="text-danger">{t("objective.blocker")}: {c.blocker}</span>}
                {c.note && <span className="text-muted-foreground">{c.note}</span>}
              </li>
            ))}
          </ul>
        )}
      <div className="rounded border p-3" data-testid="checkins-missing">
        <h2 className="mb-2 text-sm font-semibold">{t("checkin.notYet")}</h2>
        {tree.isError ? <LoadError onRetry={() => void tree.refetch()} /> : missing.length === 0 ? <p className="text-sm text-muted-foreground">{t("checkin.notYetNone")}</p> : (
          <ul className="flex flex-col gap-1 text-sm">
            {missing.map((k) => <li key={k.id} data-testid={`missing-${k.id}`}><Link href={`/goals/objectives/${objectiveOf(tree.data, k.id)}?kr=${k.id}`} className="hover:underline">{k.title}</Link></li>)}
          </ul>
        )}
      </div>
    </div>
  );
}

function objectiveOf(tree: ReturnType<typeof useGoalTree>["data"], krId: string): string {
  type O = { id: string; key_results?: { id: string }[]; children?: O[] };
  const find = (rows: O[]): string | null => {
    for (const o of rows) {
      if ((o.key_results ?? []).some((k) => k.id === krId)) return o.id;
      const hit = find(o.children ?? []);
      if (hit) return hit;
    }
    return null;
  };
  const objs = [...(tree?.strategies ?? []).flatMap((s) => s.strategic_objectives ?? []).flatMap((so) => so.objectives ?? []), ...(tree?.unaligned?.objectives ?? [])];
  return find(objs as O[]) ?? "";
}

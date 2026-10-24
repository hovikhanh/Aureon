"use client";
/** SCR-42 "Task của tôi": EP-TASK-01 `mine=true`, grouped by due (Quá hạn · Hôm nay · Tuần này · Sau đó · Không hạn), filters in the URL. */
import * as React from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { businessToday } from "@/lib/work-dates";
import { DUE_GROUPS, TASK_STATUSES, groupByDue, parseMineFilters, rangeInvalid, writeMineFilters, type MineFilters, type TaskStatus } from "./logic";
import { LoadError } from "./common";
import { TaskRow } from "./TaskRow";
import { useProjects, useTasks } from "./use-work";

export function useProjectNames() {
  const q = useProjects({ limit: 100 });
  return React.useMemo(() => new Map((q.data?.data ?? []).map((p) => [p.id, `${p.code} · ${p.name}`])), [q.data]);
}

export function MyTasksView({ onOpen }: { onOpen: (id: string) => void }) {
  const t = useTranslations("work");
  const tb = useTranslations("buttons");
  const tc = useTranslations("common");
  const sp = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const filters = React.useMemo(() => parseMineFilters(new URLSearchParams(sp.toString())), [sp]);
  const bad = rangeInvalid(filters);
  const q = useTasks({ mine: true, status: filters.statuses, due_from: filters.dueFrom, due_to: filters.dueTo, sort_by: "due_date", limit: 100 }, !bad);
  const names = useProjectNames();
  const today = businessToday();
  const groups = React.useMemo(() => groupByDue(q.data?.data ?? [], today), [q.data, today]);
  const set = (f: MineFilters) => {
    const qs = writeMineFilters(new URLSearchParams(sp.toString()), f).toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  };
  const toggle = (s: TaskStatus, on: boolean) => {
    const next = on ? [...filters.statuses, s] : filters.statuses.filter((x) => x !== s);
    set({ ...filters, statuses: TASK_STATUSES.filter((x) => next.includes(x)) });
  };
  const total = q.data?.data.length ?? 0;
  return (
    <div className="flex flex-col gap-4" data-testid="my-tasks">
      <div>
        <h2 className="text-xl font-semibold">{t("mine.title")}</h2>
        <p className="text-sm text-muted-foreground">{t("mine.hint")}</p>
      </div>
      <Card className="flex flex-wrap items-end gap-4 p-3">
        <fieldset className="flex flex-wrap items-center gap-3" data-testid="status-filter">
          <legend className="mb-1 text-xs font-medium text-muted-foreground">{t("mine.statusFilter")}</legend>
          {TASK_STATUSES.map((s) => (
            <span key={s} className="flex items-center gap-1.5">
              <Checkbox id={`st-${s}`} checked={filters.statuses.includes(s)} onCheckedChange={(v) => toggle(s, v === true)} data-testid={`status-${s}`} />
              <Label htmlFor={`st-${s}`} className="text-sm font-normal">{t(`status.${s}`)}</Label>
            </span>
          ))}
        </fieldset>
        <div className="flex items-end gap-2">
          <div className="flex flex-col gap-1">
            <Label htmlFor="due-from" className="text-xs">{t("mine.dueFrom")}</Label>
            <Input id="due-from" type="date" value={filters.dueFrom ?? ""} onChange={(e) => set({ ...filters, dueFrom: e.target.value || null })} data-testid="due-from" aria-invalid={bad} />
          </div>
          <div className="flex flex-col gap-1">
            <Label htmlFor="due-to" className="text-xs">{t("mine.dueTo")}</Label>
            <Input id="due-to" type="date" value={filters.dueTo ?? ""} onChange={(e) => set({ ...filters, dueTo: e.target.value || null })} data-testid="due-to" aria-invalid={bad} />
          </div>
          <Button variant="ghost" size="sm" onClick={() => router.replace(pathname, { scroll: false })} data-testid="clear-filters">{tb("clearFilters")}</Button>
        </div>
      </Card>
      {bad && <p role="alert" className="text-sm text-danger" data-testid="range-invalid">{t("mine.rangeInvalid")}</p>}
      {q.isError && <LoadError onRetry={() => void q.refetch()} />}
      {q.isLoading && <p className="text-sm text-muted-foreground">{tc("loading")}</p>}
      {q.isSuccess && total === 0 && <p className="text-sm text-muted-foreground" data-testid="my-tasks-empty">{t("mine.empty")}</p>}
      {q.isSuccess && DUE_GROUPS.filter((g) => groups[g].length).map((g) => (
        <section key={g} aria-labelledby={`grp-${g}`} data-testid={`group-${g}`}>
          <h3 id={`grp-${g}`} className={g === "overdue" ? "mb-1 text-sm font-semibold text-danger" : "mb-1 text-sm font-semibold"}>
            {t(`group.${g}`)} <span className="font-normal text-muted-foreground">({groups[g].length})</span>
          </h3>
          <Card className={g === "overdue" ? "border-danger/50" : undefined}>
            <ul>{groups[g].map((task) => <TaskRow key={task.id} task={task} projectName={task.project_id ? names.get(task.project_id) : null} onOpen={onOpen} />)}</ul>
          </Card>
        </section>
      ))}
    </div>
  );
}

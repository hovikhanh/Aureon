"use client";
/** SCR-56 `/work/projects/[id]`: header + late flag, key figures, tabs Tổng quan (milestones) · Task · Lịch sử. */
import * as React from "react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { formatPct, type AppLocale } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { LoadError } from "./common";
import { TASK_STATUSES } from "./logic";
import { Milestones } from "./Milestones";
import { ProgressBar } from "./ProjectsView";
import { TaskHistory } from "./TaskRelations";
import { TaskRow } from "./TaskRow";
import { TaskDetail, type DetailCaps } from "./TaskDetail";
import { useTaskPanel } from "./WorkView";
import { useProject, useTasks } from "./use-work";

type Tab = "overview" | "tasks" | "history";
const TABS: readonly Tab[] = ["overview", "tasks", "history"];
const LABEL = { overview: "tabOverview", tasks: "tabTasks", history: "tabHistory" } as const;

function Stat({ label, value, danger, testId }: { label: string; value: string; danger?: boolean; testId: string }) {
  return (
    <Card className="flex flex-col gap-1 p-3" data-testid={testId}>
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className={cn("text-xl font-semibold tabular-nums", danger && "text-danger")}>{value}</span>
    </Card>
  );
}

export function ProjectDetailView({ id, canEdit, caps }: { id: string; canEdit: boolean; caps: DetailCaps }) {
  const t = useTranslations("work");
  const locale = useLocale() as AppLocale;
  const q = useProject(id);
  const sp = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const panel = useTaskPanel();
  const tab = (TABS as readonly string[]).includes(sp.get("tab") ?? "") ? (sp.get("tab") as Tab) : "overview";
  const tasks = useTasks({ project_id: id, sort_by: "due_date", limit: 100 }, tab === "tasks");
  const setTab = (k: Tab) => router.replace(k === "overview" ? pathname : `${pathname}?tab=${k}`, { scroll: false });
  const p = q.data;
  const pct = (v: number | null | undefined) => (v === null || v === undefined ? "—" : formatPct(v, locale));
  return (
    <div className="flex flex-col gap-4" data-testid="project-detail">
      <nav aria-label={t("project.breadcrumbWork")} className="text-xs text-muted-foreground">
        <Link href="/work" className="hover:underline">{t("project.breadcrumbWork")}</Link> › <Link href="/work/projects" className="hover:underline">{t("project.breadcrumbProjects")}</Link> › <span>{p?.code ?? "…"}</span>
      </nav>
      {q.isError && <p role="alert" className="text-sm text-danger">{t("project.notFound")}</p>}
      {q.isError && <LoadError onRetry={() => void q.refetch()} />}
      {p && (
        <>
          <div className="flex flex-wrap items-center gap-3">
            <h2 className="text-2xl font-semibold" data-testid="project-title">{p.code} · {p.name}</h2>
            <Badge>{t(`projectStatus.${p.status}` as "projectStatus.active")}</Badge>
            {p.late && <Badge variant="danger" data-testid="project-late">{t("projects.late")}</Badge>}
          </div>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <Stat label={t("project.progress")} value={pct(p.progress_pct)} testId="stat-progress" />
            <Stat label={t("project.planned")} value={pct(p.planned_pct)} testId="stat-planned" />
            <Stat label={t("project.openTasks")} value={String(p.open_tasks ?? 0)} testId="stat-open" />
            <Stat label={t("project.overdueTasks")} value={String(p.overdue_tasks ?? 0)} danger={(p.overdue_tasks ?? 0) > 0} testId="stat-overdue" />
          </div>
          <ProgressBar progress={p.progress_pct} planned={p.planned_pct} />
          <div className="flex flex-wrap gap-2 text-xs" data-testid="task-counts" aria-label={t("project.byStatus")}>
            {TASK_STATUSES.map((s) => <Badge key={s} variant="outline">{t(`status.${s}`)}: {p.task_counts?.by_status?.[s] ?? 0}</Badge>)}
          </div>
          <div role="tablist" className="flex gap-1 border-b">
            {TABS.map((k) => (
              <button key={k} role="tab" type="button" aria-selected={tab === k} onClick={() => setTab(k)} data-testid={`project-tab-${k}`}
                className={cn("-mb-px border-b-2 px-3 py-1.5 text-sm", tab === k ? "border-primary text-primary" : "border-transparent text-muted-foreground")}>{t(`project.${LABEL[k]}`)}</button>
            ))}
          </div>
          {tab === "overview" && <Milestones project={p} canEdit={canEdit} />}
          {tab === "tasks" && (
            <Card>
              {tasks.isError && <LoadError onRetry={() => void tasks.refetch()} />}
              {tasks.isSuccess && !tasks.data.data.length && <p className="p-3 text-sm text-muted-foreground">{t("project.noTasks")}</p>}
              <ul data-testid="project-tasks">{(tasks.data?.data ?? []).map((task) => <TaskRow key={task.id} task={task} projectName={p.code} onOpen={panel.open} />)}</ul>
            </Card>
          )}
          {tab === "history" && <TaskHistory id={p.id} enabled={caps.canReadAudit} />}
        </>
      )}
      {panel.id && <TaskDetail id={panel.id} caps={caps} onClose={panel.close} onOpen={panel.open} />}
    </div>
  );
}

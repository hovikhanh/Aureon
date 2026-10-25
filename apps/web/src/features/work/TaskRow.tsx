"use client";
/** One task line of SCR-42 / SCR-56: title, project link, due, priority, source chip, sub-tasks, blockers, status menu. */
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { Ban, FileText, ListTree, Users, Bot, Scale, ShieldAlert } from "lucide-react";
import { formatDate, type AppLocale } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { StatusMenu } from "./common";
import type { TaskOut } from "./use-work";

const PRIORITY_VARIANT = { low: "default", medium: "primary", high: "warning", urgent: "danger" } as const;
const SOURCE_ICON = { meeting: Users, decision: Scale, ai_action: Bot, document: FileText, mitigation: ShieldAlert } as const;

/** Source link (P06) to the owning screen with a deep-link param (detail screens land in later phases). */
export function sourceHref(ref: NonNullable<TaskOut["source_ref"]>): string {
  const id = encodeURIComponent(ref.id);
  switch (ref.kind) {
    case "meeting": return `/meetings?meeting=${id}`;
    case "decision": return `/knowledge?decision=${id}`;
    case "document": return `/data?document=${id}${ref.page ? `&page=${ref.page}` : ""}`;
    case "ai_action": return `/ask?action=${id}`;
    default: return `/home?mitigation=${id}`;
  }
}

export function TaskRow({ task, projectName, onOpen }: { task: TaskOut; projectName?: string | null; onOpen: (id: string) => void }) {
  const t = useTranslations("work");
  const locale = useLocale() as AppLocale;
  const ref = task.source_ref;
  const Icon = ref ? SOURCE_ICON[ref.kind] : null;
  const priority = (task.priority in PRIORITY_VARIANT ? task.priority : "medium") as keyof typeof PRIORITY_VARIANT;
  return (
    <li className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b px-3 py-2 last:border-0" data-testid={`task-row-${task.id}`} data-status={task.status}>
      <button type="button" onClick={() => onOpen(task.id)} className="min-w-0 flex-1 truncate text-left text-sm font-medium hover:underline" aria-label={t("row.open", { title: task.title })}>
        {task.title}
      </button>
      {task.project_id && (
        <Link href={`/work/projects/${task.project_id}`} className="text-xs text-primary hover:underline" data-testid="task-project-link">{projectName ?? t("row.project")}</Link>
      )}
      <span className={task.overdue ? "text-xs font-medium text-danger" : "text-xs text-muted-foreground"} data-testid="task-due">
        {task.due_date ? t("row.due", { date: formatDate(`${task.due_date}T00:00:00+07:00`, locale) }) : t("row.noDue")}
      </span>
      <Badge variant={PRIORITY_VARIANT[priority]}>{t(`priority.${priority}`)}</Badge>
      {ref && Icon && (
        <Link href={sourceHref(ref)} className="inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs hover:bg-muted" data-testid="task-source-chip" data-kind={ref.kind}>
          <Icon className="h-3 w-3" aria-hidden />{t(`source.${ref.kind}`)}
        </Link>
      )}
      {(task.subtask_count ?? 0) > 0 && (
        <span className="inline-flex items-center gap-1 text-xs text-muted-foreground" data-testid="task-subtasks"><ListTree className="h-3 w-3" aria-hidden />{t("row.subtasks", { count: task.subtask_count ?? 0 })}</span>
      )}
      {(task.depends_on_open ?? 0) > 0 && (
        <span className="inline-flex items-center gap-1 text-xs text-warning" data-testid="task-blocked-by"><Ban className="h-3 w-3" aria-hidden />{t("row.blockedBy", { count: task.depends_on_open ?? 0 })}</span>
      )}
      <StatusMenu task={task} />
    </li>
  );
}

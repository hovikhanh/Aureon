"use client";
/** Task panel tabs: sub-tasks (EP-TASK-01 `parent_task_id` + create), dependencies (EP-TASK-06..08), history (audit). */
import * as React from "react";
import { useLocale, useTranslations } from "next-intl";
import { Trash2 } from "lucide-react";
import { apiRequest } from "@/lib/api-client";
import { formatDateTime, type AppLocale } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";
import { LoadError, useWorkError } from "./common";
import { useDependencies, useHistory, useTasks, useWorkMutation, type TaskBriefOut, type TaskOut } from "./use-work";

export function TaskSubtasks({ task, onOpen }: { task: TaskOut; onOpen: (id: string) => void }) {
  const t = useTranslations("work");
  const toast = useToast();
  const errText = useWorkError();
  const subs = useTasks({ parent_task_id: task.id });
  const [title, setTitle] = React.useState("");
  const add = useWorkMutation((v: string) => apiRequest("/work/tasks", { method: "POST", idempotent: true,
    body: { title: v, parent_task_id: task.id, assignee_id: task.assignee_id, project_id: task.project_id, due_date: task.due_date } }));
  const rows = subs.data?.data ?? [];
  const submit = async (ev: React.FormEvent) => {
    ev.preventDefault();
    if (!title.trim()) return;
    try {
      await add.mutateAsync(title.trim());
      setTitle("");
    } catch (e) {
      toast.push(errText(e), "danger");
    }
  };
  return (
    <div className="flex flex-col gap-3" data-testid="task-subtasks-panel">
      {subs.isError && <LoadError onRetry={() => void subs.refetch()} />}
      {!subs.isError && rows.length === 0 && !subs.isLoading && <p className="text-sm text-muted-foreground">{t("detail.noSubtasks")}</p>}
      <ul className="flex flex-col gap-1">
        {rows.map((s) => (
          <li key={s.id} className="flex items-center justify-between gap-2 text-sm" data-testid={`subtask-${s.id}`}>
            <button type="button" className="truncate text-left hover:underline" onClick={() => onOpen(s.id)}>{s.title}</button>
            <Badge>{t(`status.${s.status}` as "status.todo")}</Badge>
          </li>
        ))}
      </ul>
      {task.parent_task_id === null && (
        <form onSubmit={(e) => void submit(e)} className="flex gap-2">
          <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder={t("detail.subtaskPlaceholder")} aria-label={t("detail.subtaskPlaceholder")} maxLength={500} data-testid="subtask-title" />
          <Button type="submit" variant="outline" disabled={add.isPending || !title.trim()} data-testid="subtask-add">{t("detail.addSubtask")}</Button>
        </form>
      )}
    </div>
  );
}

function BriefList({ rows, onRemove, testId }: { rows: TaskBriefOut[]; onRemove?: (b: TaskBriefOut) => void; testId: string }) {
  const t = useTranslations("work");
  if (!rows.length) return <p className="text-sm text-muted-foreground">{t("detail.noDeps")}</p>;
  return (
    <ul className="flex flex-col gap-1" data-testid={testId}>
      {rows.map((b) => (
        <li key={b.dependency_id ?? b.task_id} className="flex items-center justify-between gap-2 text-sm" data-testid={`dep-${b.task_id}`}>
          <span className="truncate">{b.restricted ? t("detail.restricted") : b.title}</span>
          <span className="flex items-center gap-2">
            {!b.restricted && b.status && <Badge variant={b.overdue ? "danger" : "default"}>{t(`status.${b.status}` as "status.todo")}</Badge>}
            {onRemove && (
              <Button size="icon" variant="ghost" onClick={() => onRemove(b)} aria-label={t("detail.removeDep", { title: b.title ?? b.task_id })} data-testid={`dep-remove-${b.task_id}`}>
                <Trash2 className="h-4 w-4" />
              </Button>
            )}
          </span>
        </li>
      ))}
    </ul>
  );
}

export function TaskDeps({ task }: { task: TaskOut }) {
  const t = useTranslations("work");
  const toast = useToast();
  const errText = useWorkError();
  const deps = useDependencies(task.id);
  const candidates = useTasks({ status: ["backlog", "todo", "in_progress", "blocked", "in_review"], limit: 100 });
  const [pick, setPick] = React.useState("");
  const add = useWorkMutation((id: string) => apiRequest(`/work/tasks/${task.id}/dependencies`, { method: "POST", idempotent: true, body: { depends_on_task_id: id, dependency_type: "finish_to_start" } }));
  const remove = useWorkMutation((depId: string) => apiRequest(`/work/tasks/${task.id}/dependencies/${depId}`, { method: "DELETE" }));
  const run = async (p: Promise<unknown>) => {
    try {
      await p;
      setPick("");
    } catch (e) {
      toast.push(errText(e), "danger");
    }
  };
  const taken = new Set((deps.data?.depends_on ?? []).map((d) => d.task_id));
  const options = (candidates.data?.data ?? []).filter((c) => c.id !== task.id && !taken.has(c.id));
  return (
    <div className="flex flex-col gap-4" data-testid="task-deps-panel">
      {deps.isError && <LoadError onRetry={() => void deps.refetch()} />}
      <section className="flex flex-col gap-2">
        <h3 className="text-sm font-medium">{t("detail.dependsOn")}</h3>
        {deps.data && <BriefList rows={deps.data.depends_on} testId="deps-depends-on" onRemove={(b) => b.dependency_id && void run(remove.mutateAsync(b.dependency_id))} />}
        <div className="flex gap-2">
          <NativeSelect value={pick} onChange={(e) => setPick(e.target.value)} aria-label={t("detail.depPick")} data-testid="dep-pick">
            <option value="">{t("detail.depPick")}</option>
            {options.map((o) => <option key={o.id} value={o.id}>{o.title}</option>)}
          </NativeSelect>
          <Button variant="outline" disabled={!pick || add.isPending} onClick={() => void run(add.mutateAsync(pick))} data-testid="dep-add">{t("detail.addDep")}</Button>
        </div>
      </section>
      <section className="flex flex-col gap-2">
        <h3 className="text-sm font-medium">{t("detail.blocks")}</h3>
        {deps.data && <BriefList rows={deps.data.blocks} testId="deps-blocks" />}
      </section>
    </div>
  );
}

export function TaskHistory({ id, enabled }: { id: string; enabled: boolean }) {
  const t = useTranslations("work.detail");
  const locale = useLocale() as AppLocale;
  const q = useHistory(id, enabled);
  if (!enabled) return <p className="text-sm text-muted-foreground" data-testid="task-history-unavailable">{t("historyUnavailable")}</p>;
  if (q.isError) return <LoadError onRetry={() => void q.refetch()} />;
  const rows = q.data ?? [];
  if (!q.isLoading && !rows.length) return <p className="text-sm text-muted-foreground">{t("noHistory")}</p>;
  return (
    <ol className="flex flex-col gap-2 text-sm" data-testid="task-history">
      {rows.map((r) => (
        <li key={r.id} className="flex justify-between gap-2"><code className="text-xs">{r.action}</code><span className="text-xs text-muted-foreground">{formatDateTime(r.occurred_at, locale)}</span></li>
      ))}
    </ol>
  );
}

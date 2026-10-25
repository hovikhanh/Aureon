"use client";
/** SCR-42 detail panel `?task=<id>`: edit (rhf + zod), sub-tasks, dependencies EP-TASK-06..08, history, reassign request (EMP). */
import * as React from "react";
import { useTranslations } from "next-intl";
import { X } from "lucide-react";
import { LineageChip } from "@/components/ai/LineageChip";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { LoadError } from "./common";
import { TaskInfoForm } from "./TaskInfoForm";
import { TaskDeps, TaskHistory, TaskSubtasks } from "./TaskRelations";
import { useTask } from "./use-work";

type Tab = "info" | "subtasks" | "deps" | "history";
const TABS: readonly Tab[] = ["info", "subtasks", "deps", "history"];
const TAB_LABEL = { info: "tabInfo", subtasks: "tabSubtasks", deps: "tabDeps", history: "tabHistory" } as const;

export interface DetailCaps { isEmployee: boolean; canReadAudit: boolean; canReadOrg: boolean }

export function TaskDetail({ id, caps, onClose, onOpen }: { id: string; caps: DetailCaps; onClose: () => void; onOpen: (id: string) => void }) {
  const t = useTranslations("work.detail");
  const q = useTask(id);
  const [tab, setTab] = React.useState<Tab>("info");
  React.useEffect(() => setTab("info"), [id]);
  React.useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  const task = q.data;
  return (
    <aside role="dialog" aria-modal="false" aria-label={t("title")} data-testid="task-detail"
      className="fixed inset-y-0 right-0 z-40 flex w-full max-w-lg flex-col gap-3 overflow-y-auto border-l bg-card p-5 shadow-xl">
      <div className="flex items-start justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-lg font-semibold" data-testid="task-detail-title">{task?.title ?? t("title")}</h2>
          {task?.source_document_id && <LineageChip entity="execution.tasks" id={task.id} />}
        </div>
        <Button size="icon" variant="ghost" onClick={onClose} aria-label={t("close")} data-testid="task-detail-close"><X className="h-4 w-4" /></Button>
      </div>
      {q.isError && <p role="alert" className="text-sm text-danger">{t("notFound")}</p>}
      {q.isError && <LoadError onRetry={() => void q.refetch()} />}
      {task && (
        <>
          <div role="tablist" className="flex gap-1 border-b">
            {TABS.map((k) => (
              <button key={k} role="tab" type="button" aria-selected={tab === k} onClick={() => setTab(k)} data-testid={`task-tab-${k}`}
                className={cn("-mb-px border-b-2 px-3 py-1.5 text-sm", tab === k ? "border-primary text-primary" : "border-transparent text-muted-foreground")}>
                {t(TAB_LABEL[k])}
              </button>
            ))}
          </div>
          {tab === "info" && <TaskInfoForm key={`${task.id}:${task.version}`} task={task} caps={caps} />}
          {tab === "subtasks" && <TaskSubtasks task={task} onOpen={onOpen} />}
          {tab === "deps" && <TaskDeps task={task} />}
          {tab === "history" && <TaskHistory id={task.id} enabled={caps.canReadAudit} />}
        </>
      )}
    </aside>
  );
}

"use client";
/** Shared SCR-42 bits: error text, status change with DEC-147 menu + blocked reason, inline load error. */
import * as React from "react";
import { useTranslations } from "next-intl";
import { useQueryClient } from "@tanstack/react-query";
import { ApiError } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { useToast } from "@/components/ui/toast";
import { ConfirmDialog } from "@/features/admin/common";
import { blockingTitles, TRANSITIONS, isTaskStatus, workErrorKey, type TaskStatus } from "./logic";
import { patchTask, useWorkMutation, type TaskOut } from "./use-work";

export function useWorkError(): (e: unknown) => string {
  const t = useTranslations("work");
  return React.useCallback((e: unknown) => {
    if (!(e instanceof ApiError)) return t("errors.generic");
    if (workErrorKey(e) === "dependencyOpen") return t("toast.blockedBy", { titles: blockingTitles(e).join(", ") });
    return t(`errors.${workErrorKey(e)}` as "errors.generic");
  }, [t]);
}

export function LoadError({ onRetry, testId }: { onRetry: () => void; testId?: string }) {
  const t = useTranslations("work");
  return (
    <div role="alert" className="flex items-center gap-3 rounded border border-danger/40 bg-danger-subtle p-3 text-sm text-danger" data-testid={testId ?? "work-load-error"}>
      {t("loadError")}
      <Button size="sm" variant="outline" onClick={onRetry}>{t("retry")}</Button>
    </div>
  );
}

/** PATCH status (+ `blocked_reason`) with toast on success/error; `409` → reload (06 §3.4). */
export function useMoveTask() {
  const t = useTranslations("work");
  const toast = useToast();
  const errText = useWorkError();
  const qc = useQueryClient();
  const m = useWorkMutation((v: { task: TaskOut; to: TaskStatus; reason?: string }) =>
    patchTask(v.task, v.to === "blocked" ? { status: v.to, blocked_reason: v.reason } : { status: v.to }));
  return React.useCallback(async (task: TaskOut, to: TaskStatus, reason?: string) => {
    try {
      await m.mutateAsync({ task, to, reason });
      toast.push(t("toast.moved", { status: t(`status.${to}`) }));
      return true;
    } catch (e) {
      toast.push(errText(e), "danger");
      if (e instanceof ApiError && e.code === "CONFLICT_STATE") await qc.invalidateQueries({ queryKey: ["work"] });
      return false;
    }
  }, [m, toast, t, errText, qc]);
}

/** "Chuyển sang…" menu from `TRANSITIONS` (keyboard path for the kanban too — WCAG AA). */
export function StatusMenu({ task, testId }: { task: TaskOut; testId?: string }) {
  const t = useTranslations("work");
  const move = useMoveTask();
  const [blockedOpen, setBlockedOpen] = React.useState(false);
  const from = isTaskStatus(task.status) ? task.status : "todo";
  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button size="sm" variant="outline" data-testid={testId ?? `move-${task.id}`} aria-label={`${t("row.moveTo")} ${task.title}`}>{t(`status.${from}`)}</Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent>
          <DropdownMenuLabel>{t("row.moveTo")}</DropdownMenuLabel>
          {TRANSITIONS[from].map((to) => (
            <DropdownMenuItem key={to} data-testid={`move-to-${to}`} onSelect={() => (to === "blocked" ? setBlockedOpen(true) : void move(task, to))}>
              {t(`status.${to}`)}
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>
      <ConfirmDialog open={blockedOpen} onOpenChange={setBlockedOpen} title={t("blocked.title")} body={t("blocked.body")} confirmLabel={t("blocked.confirm")}
        reasonRequired testId="blocked-dialog" onConfirm={async (reason) => { await move(task, "blocked", reason); }} />
    </>
  );
}

"use client";
/** D-21: delete a task from its detail panel (EP-TASK-05 soft delete; a parent with sub-tasks is refused — R-DEC-42). */
import * as React from "react";
import { useTranslations } from "next-intl";
import { Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { useToast } from "@/components/ui/toast";
import { apiRequest } from "@/lib/api-client";
import { useWorkError } from "./common";
import { useWorkMutation, type TaskOut } from "./use-work";

export function TaskDelete({ task, onDeleted }: { task: Pick<TaskOut, "id" | "title">; onDeleted: () => void }) {
  const t = useTranslations("work.detail");
  const toast = useToast();
  const errorOf = useWorkError();
  const [open, setOpen] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const del = useWorkMutation(() => apiRequest(`/work/tasks/${task.id}`, { method: "DELETE" }));
  const run = () => {
    setError(null);
    del.mutate(undefined, {
      onSuccess: () => { setOpen(false); toast.push(t("deleted")); onDeleted(); },
      onError: (e) => setError(errorOf(e)),
    });
  };
  return (
    <>
      <Button size="sm" variant="outline" onClick={() => setOpen(true)} data-testid="task-delete">
        <Trash2 className="mr-1 h-4 w-4" aria-hidden />{t("delete")}
      </Button>
      <Dialog open={open} onOpenChange={(o) => { setOpen(o); if (!o) setError(null); }}>
        <DialogContent data-testid="task-delete-dialog">
          <DialogTitle>{t("deleteTitle")}</DialogTitle>
          <DialogDescription>{t("deleteConfirm", { title: task.title })}</DialogDescription>
          {error && <p role="alert" className="text-sm text-danger" data-testid="task-delete-error">{error}</p>}
          <div className="mt-4 flex justify-end gap-2">
            <DialogClose asChild><Button type="button" variant="ghost">{t("cancel")}</Button></DialogClose>
            <Button type="button" variant="danger" disabled={del.isPending} onClick={run} data-testid="task-delete-confirm">{t("delete")}</Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}

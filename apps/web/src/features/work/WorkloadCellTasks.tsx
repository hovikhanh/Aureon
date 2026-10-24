"use client";
/** SCR-57 cell drill-down (F5 entry, 06 §4.5): open tasks of one person due in one ISO week (EP-TASK-01 `assignee_id` + `due_from/due_to`). */
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { formatDate, type AppLocale } from "@/lib/format";
import { weekRange } from "@/lib/work-dates";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { DEFAULT_STATUSES } from "./logic";
import { LoadError } from "./common";
import { useTasks } from "./use-work";

export function WorkloadCellTasks({ employeeId, week, name, onClose }: { employeeId: string; week: string; name: string; onClose: () => void }) {
  const t = useTranslations("work");
  const locale = useLocale() as AppLocale;
  const { start, end } = weekRange(week);
  const q = useTasks({ assignee_id: employeeId, due_from: start, due_to: end, status: DEFAULT_STATUSES, sort_by: "due_date", limit: 100 });
  const rows = q.data?.data ?? [];
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-lg" data-testid="wl-cell-dialog">
        <DialogTitle>{t("workload.cellTasks", { name, week })}</DialogTitle>
        <DialogDescription className="sr-only">{t("workload.cellTasks", { name, week })}</DialogDescription>
        {q.isError && <LoadError onRetry={() => void q.refetch()} />}
        {q.isSuccess && !rows.length && <p className="mt-3 text-sm text-muted-foreground">{t("workload.noCellTasks")}</p>}
        <ul className="mt-3 flex flex-col gap-2" data-testid="wl-cell-tasks">
          {rows.map((task) => (
            <li key={task.id} className="flex items-center justify-between gap-2 text-sm">
              <Link href={`/work?task=${task.id}`} className="truncate hover:underline">{task.title}</Link>
              <span className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground">{task.due_date ? formatDate(`${task.due_date}T00:00:00+07:00`, locale) : "—"}</span>
                <Badge>{t(`status.${task.status}` as "status.todo")}</Badge>
              </span>
            </li>
          ))}
        </ul>
      </DialogContent>
    </Dialog>
  );
}

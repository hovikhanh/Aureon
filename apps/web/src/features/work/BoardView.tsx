"use client";
/**
 * SCR-42 tab "Nhóm" (kanban, R-DEC-48): columns backlog…done (+cancelled toggle), filters
 * department (MGR pinned) / assignee / project; drag-drop = PATCH status+version (wrong rule →
 * card snaps back + toast; 409 → reload); keyboard path = "Chuyển sang…" menu; ≤ 50 cards/column.
 */
import * as React from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";
import { BOARD_COLUMN_LIMIT, boardColumns, canMove, groupByStatus, type TaskStatus } from "./logic";
import { LoadError, StatusMenu, useMoveTask } from "./common";
import { CreateTaskDialog } from "./CreateTaskDialog";
import { useProjectNames } from "./MyTasksView";
import { useMembers, useTasks, type Member, type TaskOut } from "./use-work";

/** `pinned` (MGR): the department filter is locked to the own department (EP-ORG-24 returns only it for MGR). */
export function BoardView({ pinned, canReadOrg, onOpen }: { pinned: boolean; canReadOrg: boolean; onOpen: (id: string) => void }) {
  const t = useTranslations("work");
  const toast = useToast();
  const move = useMoveTask();
  const members = useMembers(canReadOrg);
  const names = useProjectNames();
  const [chosen, setDept] = React.useState("");
  const [assignee, setAssignee] = React.useState("");
  const [project, setProject] = React.useState("");
  const [showCancelled, setShowCancelled] = React.useState(false);
  const [expanded, setExpanded] = React.useState<Set<string>>(new Set());
  const [creating, setCreating] = React.useState(false);
  const [dragging, setDragging] = React.useState<TaskOut | null>(null);
  const memberList: Member[] = members.data ?? [];
  const pinnedDepartment = pinned ? memberList[0]?.department_id ?? null : null;
  const dept = pinnedDepartment ?? chosen;
  const q = useTasks({ department_id: dept || null, assignee_id: assignee || null, project_id: project || null, sort_by: "due_date", limit: 100 });
  const cols = boardColumns(showCancelled);
  const grouped = groupByStatus(q.data?.data ?? [], cols);
  const nameOf = new Map(memberList.map((m) => [m.employee_id, m.full_name]));
  const departments = [...new Map(memberList.map((m) => [m.department_id, m.department_name])).entries()];
  const people = memberList.filter((m) => !dept || m.department_id === dept);
  const drop = async (e: React.DragEvent, to: TaskStatus) => {
    e.preventDefault();
    const id = e.dataTransfer.getData("text/plain") || dragging?.id;
    const task = (q.data?.data ?? []).find((x) => x.id === id);
    setDragging(null);
    if (!task || task.status === to) return;
    if (to === "blocked") return toast.push(t("errors.blockedReason"), "danger");
    if (!canMove(task.status, to)) return toast.push(t("errors.transition"), "danger"); // snaps back (no optimistic move)
    await move(task, to);
  };
  return (
    <div className="flex flex-col gap-4" data-testid="board">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold">{t("board.title")}</h2>
          <p className="text-sm text-muted-foreground">{t("board.hint")}</p>
        </div>
        <Button onClick={() => setCreating(true)} data-testid="board-assign">{t("board.assign")}</Button>
      </div>
      <Card className="flex flex-wrap items-end gap-3 p-3">
        <div className="flex flex-col gap-1">
          <Label htmlFor="bf-dept" className="text-xs">{t("board.department")}</Label>
          <NativeSelect id="bf-dept" value={dept} disabled={Boolean(pinnedDepartment)} onChange={(e) => { setDept(e.target.value); setAssignee(""); }} data-testid="board-dept">
            {!pinnedDepartment && <option value="">{t("board.allDepartments")}</option>}
            {departments.map(([id, name]) => <option key={id} value={id}>{name}</option>)}
          </NativeSelect>
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor="bf-assignee" className="text-xs">{t("board.assignee")}</Label>
          <NativeSelect id="bf-assignee" value={assignee} onChange={(e) => setAssignee(e.target.value)} data-testid="board-assignee">
            <option value="">{t("board.allAssignees")}</option>
            {people.map((m) => <option key={m.employee_id} value={m.employee_id}>{m.employee_code} · {m.full_name}</option>)}
          </NativeSelect>
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor="bf-project" className="text-xs">{t("board.project")}</Label>
          <NativeSelect id="bf-project" value={project} onChange={(e) => setProject(e.target.value)} data-testid="board-project">
            <option value="">{t("board.allProjects")}</option>
            {[...names.entries()].map(([id, name]) => <option key={id} value={id}>{name}</option>)}
          </NativeSelect>
        </div>
        <span className="flex items-center gap-1.5 pb-2">
          <Checkbox id="bf-cancelled" checked={showCancelled} onCheckedChange={(v) => setShowCancelled(v === true)} data-testid="board-show-cancelled" />
          <Label htmlFor="bf-cancelled" className="text-sm font-normal">{t("board.showCancelled")}</Label>
        </span>
      </Card>
      {q.isError && <LoadError onRetry={() => void q.refetch()} />}
      <div className="grid auto-cols-[minmax(14rem,1fr)] grid-flow-col gap-3 overflow-x-auto pb-2">
        {cols.map((c) => {
          const cards = grouped[c] ?? [];
          const shown = expanded.has(c) ? cards : cards.slice(0, BOARD_COLUMN_LIMIT);
          return (
            <section key={c} aria-label={t(`status.${c}`)} data-testid={`col-${c}`} onDragOver={(e) => e.preventDefault()} onDrop={(e) => void drop(e, c)}
              className="flex min-h-40 flex-col gap-2 rounded-lg bg-muted/50 p-2">
              <h3 className="flex justify-between px-1 text-sm font-semibold">{t(`status.${c}`)}<span className="text-xs font-normal text-muted-foreground">{t("board.columnCount", { count: cards.length })}</span></h3>
              {shown.map((task) => (
                <article key={task.id} draggable onDragStart={(e) => { e.dataTransfer.setData("text/plain", task.id); e.dataTransfer.effectAllowed = "move"; setDragging(task); }} onDragEnd={() => setDragging(null)} data-testid={`card-${task.id}`}
                  className="flex cursor-grab flex-col gap-2 rounded border bg-card p-2 text-sm shadow-sm">
                  <button type="button" className="text-left font-medium hover:underline" onClick={() => onOpen(task.id)}>{task.title}</button>
                  <span className="text-xs text-muted-foreground">{task.assignee_id ? nameOf.get(task.assignee_id) ?? task.assignee_id.slice(0, 8) : t("board.unassigned")}</span>
                  <StatusMenu task={task} testId={`card-move-${task.id}`} />
                </article>
              ))}
              {cards.length > shown.length && (
                <Button variant="ghost" size="sm" onClick={() => setExpanded(new Set([...expanded, c]))} data-testid={`col-more-${c}`}>{t("board.more")}</Button>
              )}
            </section>
          );
        })}
      </div>
      <CreateTaskDialog open={creating} onOpenChange={setCreating} members={people} />
    </div>
  );
}

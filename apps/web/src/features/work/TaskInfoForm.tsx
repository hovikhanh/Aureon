"use client";
/** "Thông tin" tab of the task panel — rhf + zod; EMP cannot change assignee and gets the reassign request instead. */
import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";
import { Field } from "@/features/admin/common";
import { PRIORITIES } from "./logic";
import { useWorkError } from "./common";
import { ReassignDialog } from "./ReassignDialog";
import { taskFormSchema, toTaskBody, type TaskFormValues } from "./task-form";
import { patchTask, useMembers, useWorkMutation, type TaskOut } from "./use-work";
import type { DetailCaps } from "./TaskDetail";

const valuesOf = (task: TaskOut): TaskFormValues => ({
  title: task.title, description: task.description ?? "", start_date: task.start_date ?? "", due_date: task.due_date ?? "",
  priority: (PRIORITIES as readonly string[]).includes(task.priority) ? (task.priority as TaskFormValues["priority"]) : "medium",
  estimate_hours: task.estimate_hours === null || task.estimate_hours === undefined ? "" : String(task.estimate_hours), assignee_id: task.assignee_id ?? "",
});

export function TaskInfoForm({ task, caps }: { task: TaskOut; caps: DetailCaps }) {
  const t = useTranslations("work");
  const tb = useTranslations("buttons");
  const toast = useToast();
  const errText = useWorkError();
  const members = useMembers(caps.canReadOrg && !caps.isEmployee);
  const [reassignOpen, setReassignOpen] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const schema = React.useMemo(() => taskFormSchema({ titleRequired: t("detail.titleRequired"), dueBeforeStart: t("detail.dueBeforeStart"), estimateInvalid: t("detail.estimateInvalid") }), [t]);
  const initial = React.useMemo(() => valuesOf(task), [task]);
  const form = useForm<TaskFormValues>({ resolver: zodResolver(schema), defaultValues: initial });
  const save = useWorkMutation((body: Record<string, unknown>) => patchTask(task, body));
  const e = form.formState.errors;
  const submit = form.handleSubmit(async (v) => {
    setError(null);
    const before = { ...toTaskBody(initial) } as Partial<Record<keyof TaskFormValues, unknown>>;
    const body = toTaskBody(v, before);
    if (caps.isEmployee) delete body.assignee_id;
    if (!Object.keys(body).length) return;
    try {
      await save.mutateAsync(body);
      toast.push(t("toast.saved"));
    } catch (err) {
      setError(errText(err));
    }
  });
  const closed = task.status === "done" || task.status === "cancelled";
  return (
    <form onSubmit={(ev) => void submit(ev)} className="flex flex-col gap-3" data-testid="task-form" noValidate>
      <Field id="tf-title" label={t("detail.fieldTitle")} error={e.title?.message}><Input id="tf-title" {...form.register("title")} aria-invalid={Boolean(e.title)} data-testid="tf-title" /></Field>
      <Field id="tf-desc" label={t("detail.fieldDescription")}>
        <textarea id="tf-desc" rows={3} {...form.register("description")} className="rounded border bg-card px-3 py-2 text-sm" data-testid="tf-desc" />
      </Field>
      <div className="grid grid-cols-2 gap-3">
        <Field id="tf-start" label={t("detail.fieldStart")}><Input id="tf-start" type="date" {...form.register("start_date")} data-testid="tf-start" /></Field>
        <Field id="tf-due" label={t("detail.fieldDue")} error={e.due_date?.message}><Input id="tf-due" type="date" {...form.register("due_date")} aria-invalid={Boolean(e.due_date)} data-testid="tf-due" /></Field>
        <Field id="tf-priority" label={t("detail.fieldPriority")}>
          <NativeSelect id="tf-priority" {...form.register("priority")} data-testid="tf-priority">
            {PRIORITIES.map((p) => <option key={p} value={p}>{t(`priority.${p}`)}</option>)}
          </NativeSelect>
        </Field>
        <Field id="tf-est" label={t("detail.fieldEstimate")} error={e.estimate_hours?.message}><Input id="tf-est" inputMode="decimal" {...form.register("estimate_hours")} data-testid="tf-est" /></Field>
      </div>
      {!caps.isEmployee && members.data && (
        <Field id="tf-assignee" label={t("detail.fieldAssignee")}>
          <NativeSelect id="tf-assignee" {...form.register("assignee_id")} data-testid="tf-assignee">
            <option value="">{t("board.unassigned")}</option>
            {members.data.map((m) => <option key={m.employee_id} value={m.employee_id}>{m.employee_code} · {m.full_name}</option>)}
          </NativeSelect>
        </Field>
      )}
      {task.status === "blocked" && task.blocked_reason && <p className="text-sm text-warning" data-testid="tf-blocked-reason">{t("detail.blockedReason")}: {task.blocked_reason}</p>}
      {error && <p role="alert" className="text-sm text-danger" data-testid="task-form-error">{error}</p>}
      <div className="flex flex-wrap justify-end gap-2">
        {caps.isEmployee && !closed && <Button type="button" variant="outline" onClick={() => setReassignOpen(true)} data-testid="request-reassign">{t("detail.requestReassign")}</Button>}
        <Button type="submit" disabled={save.isPending} data-testid="task-save">{tb("save")}</Button>
      </div>
      {caps.isEmployee && <ReassignDialog open={reassignOpen} onOpenChange={setReassignOpen} task={task} />}
    </form>
  );
}

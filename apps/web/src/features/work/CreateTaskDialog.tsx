"use client";
/** "Giao việc" (SCR-42 Nhóm): EP-TASK-02 with an assignee picked from EP-ORG-24 `members[]`. */
import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslations } from "next-intl";
import { apiRequest } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";
import { Field } from "@/features/admin/common";
import { PRIORITIES } from "./logic";
import { useWorkError } from "./common";
import { taskFormSchema, toTaskBody, type TaskFormValues } from "./task-form";
import { useWorkMutation, type Member } from "./use-work";

const EMPTY: TaskFormValues = { title: "", description: "", start_date: "", due_date: "", priority: "medium", estimate_hours: "", assignee_id: "" };

export function CreateTaskDialog({ open, onOpenChange, members }: { open: boolean; onOpenChange: (o: boolean) => void; members: Member[] }) {
  const t = useTranslations("work");
  const tb = useTranslations("buttons");
  const toast = useToast();
  const errText = useWorkError();
  const schema = React.useMemo(() => taskFormSchema({ titleRequired: t("detail.titleRequired"), dueBeforeStart: t("detail.dueBeforeStart"), estimateInvalid: t("detail.estimateInvalid") }), [t]);
  const form = useForm<TaskFormValues>({ resolver: zodResolver(schema), defaultValues: EMPTY });
  const [error, setError] = React.useState<string | null>(null);
  React.useEffect(() => { if (open) { form.reset(EMPTY); setError(null); } }, [open, form]);
  const create = useWorkMutation((body: Record<string, unknown>) => apiRequest("/work/tasks", { method: "POST", body, idempotent: true }));
  const e = form.formState.errors;
  const submit = form.handleSubmit(async (v) => {
    setError(null);
    const body = toTaskBody(v);
    const m = members.find((x) => x.employee_id === v.assignee_id);
    try {
      await create.mutateAsync(m ? { ...body, department_id: m.department_id } : body);
      toast.push(t("toast.created"));
      onOpenChange(false);
    } catch (err) {
      setError(errText(err));
    }
  });
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="create-task-dialog">
        <DialogTitle>{t("create.title")}</DialogTitle>
        <DialogDescription className="sr-only">{t("create.title")}</DialogDescription>
        <form onSubmit={(ev) => void submit(ev)} className="mt-4 flex flex-col gap-3" noValidate>
          <Field id="ct-title" label={t("detail.fieldTitle")} error={e.title?.message}><Input id="ct-title" {...form.register("title")} aria-invalid={Boolean(e.title)} data-testid="ct-title" /></Field>
          <Field id="ct-assignee" label={t("create.assignee")}>
            <NativeSelect id="ct-assignee" {...form.register("assignee_id")} data-testid="ct-assignee">
              <option value="">{t("create.none")}</option>
              {members.map((m) => <option key={m.employee_id} value={m.employee_id}>{m.employee_code} · {m.full_name}</option>)}
            </NativeSelect>
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field id="ct-due" label={t("detail.fieldDue")} error={e.due_date?.message}><Input id="ct-due" type="date" {...form.register("due_date")} data-testid="ct-due" /></Field>
            <Field id="ct-priority" label={t("detail.fieldPriority")}>
              <NativeSelect id="ct-priority" {...form.register("priority")} data-testid="ct-priority">
                {PRIORITIES.map((p) => <option key={p} value={p}>{t(`priority.${p}`)}</option>)}
              </NativeSelect>
            </Field>
            <Field id="ct-est" label={t("detail.fieldEstimate")} error={e.estimate_hours?.message}><Input id="ct-est" inputMode="decimal" {...form.register("estimate_hours")} data-testid="ct-est" /></Field>
          </div>
          {error && <p role="alert" className="text-sm text-danger" data-testid="create-task-error">{error}</p>}
          <div className="flex justify-end gap-2">
            <DialogClose asChild><Button type="button" variant="ghost">{tb("cancel")}</Button></DialogClose>
            <Button type="submit" disabled={create.isPending} data-testid="ct-submit">{t("create.submit")}</Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

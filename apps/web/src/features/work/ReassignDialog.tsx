"use client";
/**
 * EMP "Đề nghị chuyển người" (EP-TASK-19). Picker from EP-ORG-24 `members[]` when readable; EMP gets
 * 403 there (10 §7.2.1) → manual employee-ID input with validation (parent decision, OQ raised to 13).
 */
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
import { useWorkError } from "./common";
import { reassignSchema, type ReassignValues } from "./task-form";
import { useMembers, useWorkMutation, type TaskOut } from "./use-work";

export function ReassignDialog({ open, onOpenChange, task }: { open: boolean; onOpenChange: (o: boolean) => void; task: TaskOut }) {
  const t = useTranslations("work.reassign");
  const tb = useTranslations("buttons");
  const tw = useTranslations("work");
  const toast = useToast();
  const errText = useWorkError();
  const members = useMembers(open);
  const pick = (members.data ?? []).filter((m) => m.employee_id !== task.assignee_id);
  const schema = React.useMemo(() => reassignSchema({ toInvalid: t("toInvalid"), reasonRequired: t("reasonRequired") }), [t]);
  const form = useForm<ReassignValues>({ resolver: zodResolver(schema), defaultValues: { to_assignee_id: "", reason: "" } });
  const [error, setError] = React.useState<string | null>(null);
  React.useEffect(() => { if (open) { form.reset({ to_assignee_id: "", reason: "" }); setError(null); } }, [open, form]);
  const send = useWorkMutation((v: ReassignValues) => apiRequest(`/work/tasks/${task.id}/reassign-requests`, { method: "POST", body: v, idempotent: true }));
  const e = form.formState.errors;
  const submit = form.handleSubmit(async (v) => {
    setError(null);
    try {
      await send.mutateAsync(v);
      toast.push(tw("toast.reassignSent"));
      onOpenChange(false);
    } catch (err) {
      setError(errText(err));
    }
  });
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="reassign-dialog">
        <DialogTitle>{t("title")}</DialogTitle>
        <DialogDescription className="mt-1">{t("body")}</DialogDescription>
        <form onSubmit={(ev) => void submit(ev)} className="mt-4 flex flex-col gap-3" noValidate>
          {pick.length > 0 ? (
            <Field id="ra-to" label={t("to")} error={e.to_assignee_id?.message}>
              <NativeSelect id="ra-to" {...form.register("to_assignee_id")} data-testid="reassign-to">
                <option value="">{t("toPlaceholder")}</option>
                {pick.map((m) => <option key={m.employee_id} value={m.employee_id}>{m.employee_code} · {m.full_name}</option>)}
              </NativeSelect>
            </Field>
          ) : (
            <Field id="ra-to" label={t("toManual")} error={e.to_assignee_id?.message}>
              <Input id="ra-to" {...form.register("to_assignee_id")} aria-invalid={Boolean(e.to_assignee_id)} aria-describedby="ra-to-hint" data-testid="reassign-to-id" />
              <span id="ra-to-hint" className="text-xs text-muted-foreground">{t("toManualHint")}</span>
            </Field>
          )}
          <Field id="ra-reason" label={t("reason")} error={e.reason?.message}>
            <textarea id="ra-reason" rows={3} maxLength={500} {...form.register("reason")} aria-invalid={Boolean(e.reason)} className="rounded border bg-card px-3 py-2 text-sm" data-testid="reassign-reason" />
          </Field>
          {error && <p role="alert" className="text-sm text-danger" data-testid="reassign-error">{error}</p>}
          <div className="flex justify-end gap-2">
            <DialogClose asChild><Button type="button" variant="ghost">{tb("cancel")}</Button></DialogClose>
            <Button type="submit" disabled={send.isPending} data-testid="reassign-submit">{t("submit")}</Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

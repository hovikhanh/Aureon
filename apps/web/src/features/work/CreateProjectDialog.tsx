"use client";
/** SCR-55 "Tạo dự án" (EP-TASK-10, MGR+): owner = the signed-in user; MGR department is pinned server-side. */
import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useTranslations } from "next-intl";
import { apiRequest } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import { Field } from "@/features/admin/common";
import { useWorkError } from "./common";
import { useWorkMutation } from "./use-work";

export function CreateProjectDialog({ open, onOpenChange, ownerId }: { open: boolean; onOpenChange: (o: boolean) => void; ownerId: string }) {
  const t = useTranslations("work");
  const tb = useTranslations("buttons");
  const toast = useToast();
  const errText = useWorkError();
  const schema = React.useMemo(() => z.object({
    code: z.string().trim().min(1, t("projects.codeRequired")).max(50),
    name: z.string().trim().min(1, t("projects.nameRequired")).max(300),
    start_date: z.string(),
    due_date: z.string(),
  }).refine((v) => !v.start_date || !v.due_date || v.due_date >= v.start_date, { path: ["due_date"], message: t("detail.dueBeforeStart") }), [t]);
  type V = z.infer<typeof schema>;
  const form = useForm<V>({ resolver: zodResolver(schema), defaultValues: { code: "", name: "", start_date: "", due_date: "" } });
  const [error, setError] = React.useState<string | null>(null);
  React.useEffect(() => { if (open) { form.reset(); setError(null); } }, [open, form]);
  const create = useWorkMutation((body: Record<string, unknown>) => apiRequest("/work/projects", { method: "POST", body, idempotent: true }));
  const e = form.formState.errors;
  const submit = form.handleSubmit(async (v) => {
    setError(null);
    try {
      await create.mutateAsync({ code: v.code.trim(), name: v.name.trim(), owner_id: ownerId, start_date: v.start_date || null, due_date: v.due_date || null, status: "planned" });
      toast.push(t("projects.created"));
      onOpenChange(false);
    } catch (err) {
      setError(errText(err));
    }
  });
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="create-project-dialog">
        <DialogTitle>{t("projects.createTitle")}</DialogTitle>
        <DialogDescription className="sr-only">{t("projects.createTitle")}</DialogDescription>
        <form onSubmit={(ev) => void submit(ev)} className="mt-4 flex flex-col gap-3" noValidate>
          <Field id="cp-code" label={t("projects.fieldCode")} error={e.code?.message}><Input id="cp-code" {...form.register("code")} data-testid="cp-code" /></Field>
          <Field id="cp-name" label={t("projects.fieldName")} error={e.name?.message}><Input id="cp-name" {...form.register("name")} data-testid="cp-name" /></Field>
          <div className="grid grid-cols-2 gap-3">
            <Field id="cp-start" label={t("projects.fieldStart")}><Input id="cp-start" type="date" {...form.register("start_date")} data-testid="cp-start" /></Field>
            <Field id="cp-due" label={t("projects.fieldDue")} error={e.due_date?.message}><Input id="cp-due" type="date" {...form.register("due_date")} data-testid="cp-due" /></Field>
          </div>
          {error && <p role="alert" className="text-sm text-danger" data-testid="create-project-error">{error}</p>}
          <div className="flex justify-end gap-2">
            <DialogClose asChild><Button type="button" variant="ghost">{tb("cancel")}</Button></DialogClose>
            <Button type="submit" disabled={create.isPending} data-testid="cp-submit">{t("projects.create")}</Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

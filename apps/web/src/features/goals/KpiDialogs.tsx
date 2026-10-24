"use client";
/** SCR-58 actions: "Ghi số đo" (EP-KPI-07) and "Đặt target kỳ" (EP-KPI-09, not EMP) — Idempotency-Key via `idempotent: true`. */
import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useLocale, useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import { Field } from "@/features/admin/common";
import { formatPeriod, type AppLocale } from "@/lib/format";
import { useGoalError } from "./common";
import { measureSchema, targetSchema, toMeasureBody, toTargetBody, type MeasureValues, type TargetValues } from "./forms";
import { postMeasurement, postTarget, useGoalMutation } from "./use-goals";

interface Props { open: boolean; onOpenChange: (o: boolean) => void; kpiId: string; period: string }

export function MeasureDialog({ open, onOpenChange, kpiId, period }: Props) {
  const t = useTranslations("goals");
  const toast = useToast();
  const errText = useGoalError();
  const schema = React.useMemo(() => measureSchema({ valueRequired: t("form.valueRequired"), periodInvalid: t("form.periodInvalid"), tooLong: t("form.tooLong") }), [t]);
  const form = useForm<MeasureValues>({ resolver: zodResolver(schema), defaultValues: { period_key: period, actual_value: "", note: "" } });
  const [error, setError] = React.useState<string | null>(null);
  React.useEffect(() => { if (open) { form.reset({ period_key: period, actual_value: "", note: "" }); setError(null); } }, [open, form, period]);
  const m = useGoalMutation((v: MeasureValues) => postMeasurement(kpiId, toMeasureBody(v)));
  const e = form.formState.errors;
  const submit = form.handleSubmit(async (v) => {
    setError(null);
    try { await m.mutateAsync(v); toast.push(t("toast.measured")); onOpenChange(false); } catch (err) { setError(errText(err)); }
  });
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="measure-dialog">
        <DialogTitle>{t("kpi.measure")}</DialogTitle>
        <DialogDescription className="sr-only">{t("kpi.measure")}</DialogDescription>
        <form onSubmit={(ev) => void submit(ev)} className="mt-4 flex flex-col gap-3" noValidate>
          <Field id="m-period" label={t("form.period")} error={e.period_key?.message}><Input id="m-period" {...form.register("period_key")} data-testid="m-period" /></Field>
          <Field id="m-value" label={t("form.value")} error={e.actual_value?.message}><Input id="m-value" inputMode="decimal" {...form.register("actual_value")} data-testid="m-value" /></Field>
          <Field id="m-note" label={t("form.note")} error={e.note?.message}><Input id="m-note" {...form.register("note")} data-testid="m-note" /></Field>
          {error && <p role="alert" className="text-sm text-danger" data-testid="measure-error">{error}</p>}
          <div className="flex justify-end gap-2">
            <DialogClose asChild><Button type="button" variant="ghost">{t("form.cancel")}</Button></DialogClose>
            <Button type="submit" disabled={m.isPending} data-testid="m-submit">{t("form.save")}</Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export function TargetDialog({ open, onOpenChange, kpiId, period }: Props) {
  const t = useTranslations("goals");
  const locale = useLocale() as AppLocale;
  const toast = useToast();
  const errText = useGoalError();
  const schema = React.useMemo(() => targetSchema({ valueRequired: t("form.valueRequired"), periodInvalid: t("form.periodInvalid"), dateInvalid: t("form.dateInvalid"), tooLong: t("form.tooLong") }), [t]);
  const blank = React.useMemo(() => ({ period_key: period, target: "", valid_from: "", reason: "" }), [period]);
  const form = useForm<TargetValues>({ resolver: zodResolver(schema), defaultValues: blank });
  const [error, setError] = React.useState<string | null>(null);
  React.useEffect(() => { if (open) { form.reset(blank); setError(null); } }, [open, form, blank]);
  const m = useGoalMutation((v: TargetValues) => postTarget(kpiId, toTargetBody(v)));
  const e = form.formState.errors;
  const submit = form.handleSubmit(async (v) => {
    setError(null);
    try { await m.mutateAsync(v); toast.push(t("toast.targetSet", { period: formatPeriod(v.period_key, locale) })); onOpenChange(false); } catch (err) { setError(errText(err)); }
  });
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="target-dialog">
        <DialogTitle>{t("kpi.setTarget")}</DialogTitle>
        <DialogDescription className="sr-only">{t("kpi.setTarget")}</DialogDescription>
        <form onSubmit={(ev) => void submit(ev)} className="mt-4 flex flex-col gap-3" noValidate>
          <Field id="t-period" label={t("form.period")} error={e.period_key?.message}><Input id="t-period" {...form.register("period_key")} data-testid="t-period" /></Field>
          <Field id="t-target" label={t("form.target")} error={e.target?.message}><Input id="t-target" inputMode="decimal" {...form.register("target")} data-testid="t-target" /></Field>
          <Field id="t-from" label={t("form.validFrom")} error={e.valid_from?.message}><Input id="t-from" type="date" {...form.register("valid_from")} data-testid="t-from" /></Field>
          <Field id="t-reason" label={t("form.reason")} error={e.reason?.message}><Input id="t-reason" {...form.register("reason")} data-testid="t-reason" /></Field>
          {error && <p role="alert" className="text-sm text-danger" data-testid="target-error">{error}</p>}
          <div className="flex justify-end gap-2">
            <DialogClose asChild><Button type="button" variant="ghost">{t("form.cancel")}</Button></DialogClose>
            <Button type="submit" disabled={m.isPending} data-testid="t-submit">{t("form.save")}</Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

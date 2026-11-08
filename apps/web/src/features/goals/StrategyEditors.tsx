"use client";
/** Create dialogs of `/goals/strategies` (EP-STR-03, EP-STR-08): the API enforces who may write and where. */
import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslations } from "next-intl";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";
import { Field } from "@/features/admin/common";
import { DepartmentSelect, Shell, useMessages, useOwners } from "./GoalEditors";
import type { GoalCaps } from "./GoalsShell";
import { useGoalError } from "./common";
import { GOAL_STATUSES, PILLARS, strategicObjectiveSchema, strategySchema, toStrategicObjectiveCreate, toStrategyCreate, type StrategicObjectiveValues, type StrategyValues } from "./goal-forms";
import { createStrategicObjective, createStrategy, useGoalMutation, type StrategyOut } from "./use-goals";

interface Open { open: boolean; onOpenChange: (open: boolean) => void; caps: GoalCaps }

export function StrategyDialog({ open, onOpenChange, caps }: Open) {
  const t = useTranslations("goals.strategy");
  const te = useTranslations("goals.editor");
  const toast = useToast();
  const errText = useGoalError();
  const msgs = useMessages();
  const blank = React.useMemo<StrategyValues>(() => ({ code: "", name: "", period_start: "", period_end: "", status: "draft", owner_id: caps.userId }), [caps.userId]);
  const form = useForm<StrategyValues>({
    resolver: zodResolver(strategySchema({ ...msgs, dateInvalid: t("dateInvalid"), endBeforeStart: t("endBeforeStart") })),
    defaultValues: blank,
  });
  const [error, setError] = React.useState<string | null>(null);
  React.useEffect(() => { if (open) { form.reset(blank); setError(null); } }, [open, form, blank]);
  const owners = useOwners(caps);
  const m = useGoalMutation((v: StrategyValues) => createStrategy(toStrategyCreate(v)));
  const e = form.formState.errors;
  const submit = form.handleSubmit(async (v) => {
    setError(null);
    try {
      const out = await m.mutateAsync(v);
      toast.push(t("created", { code: out.code }));
      onOpenChange(false);
    } catch (err) { setError(errText(err)); }
  });
  return (
    <Shell open={open} onOpenChange={onOpenChange} title={t("create")} testId="strategy-editor" error={error} pending={m.isPending} onSubmit={(ev) => void submit(ev)}>
      <Field id="st-code" required label={t("code")} error={e.code?.message}><Input id="st-code" {...form.register("code")} data-testid="st-code" /></Field>
      <Field id="st-name" required label={t("name")} error={e.name?.message}><Input id="st-name" {...form.register("name")} data-testid="st-name" /></Field>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field id="st-start" required label={t("periodStart")} error={e.period_start?.message}><Input id="st-start" type="date" {...form.register("period_start")} data-testid="st-start" /></Field>
        <Field id="st-end" required label={t("periodEnd")} error={e.period_end?.message}><Input id="st-end" type="date" {...form.register("period_end")} data-testid="st-end" /></Field>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field id="st-status" label={t("status")}>
          <NativeSelect id="st-status" {...form.register("status")} data-testid="st-status">
            {GOAL_STATUSES.map((s) => <option key={s} value={s}>{te(`status.${s}`)}</option>)}
          </NativeSelect>
        </Field>
        <Field id="st-owner" required label={te("owner")} error={e.owner_id?.message}>
          <NativeSelect id="st-owner" {...form.register("owner_id")} data-testid="st-owner">{owners.map((o) => <option key={o.id} value={o.id}>{o.label}</option>)}</NativeSelect>
        </Field>
      </div>
    </Shell>
  );
}

export function StrategicObjectiveDialog({ open, onOpenChange, caps, strategy }: Open & { strategy: StrategyOut }) {
  const t = useTranslations("goals.strategy");
  const te = useTranslations("goals.editor");
  const tp = useTranslations("goals.pillar");
  const toast = useToast();
  const errText = useGoalError();
  const msgs = useMessages();
  const blank = React.useMemo<StrategicObjectiveValues>(() => ({ code: "", title: "", pillar: "", owner_id: caps.userId, department_id: "" }), [caps.userId]);
  const form = useForm<StrategicObjectiveValues>({ resolver: zodResolver(strategicObjectiveSchema(msgs)), defaultValues: blank });
  const [error, setError] = React.useState<string | null>(null);
  React.useEffect(() => { if (open) { form.reset(blank); setError(null); } }, [open, form, blank]);
  const owners = useOwners(caps);
  const m = useGoalMutation((v: StrategicObjectiveValues) => createStrategicObjective(toStrategicObjectiveCreate(strategy.id, v)));
  const e = form.formState.errors;
  const pillars = caps.scopePillars.length ? PILLARS.filter((p) => caps.scopePillars.includes(p)) : PILLARS;
  const submit = form.handleSubmit(async (v) => {
    setError(null);
    try {
      const out = await m.mutateAsync(v);
      toast.push(t("soCreated", { code: out.code }));
      onOpenChange(false);
    } catch (err) { setError(errText(err)); }
  });
  return (
    <Shell open={open} onOpenChange={onOpenChange} title={t("createSo")} testId="so-editor" error={error} pending={m.isPending} onSubmit={(ev) => void submit(ev)}>
      <Field id="so-code" required label={t("code")} error={e.code?.message}><Input id="so-code" {...form.register("code")} data-testid="so-code" /></Field>
      <Field id="so-title" required label={t("soName")} error={e.title?.message}><Input id="so-title" {...form.register("title")} data-testid="so-title" /></Field>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field id="so-pillar" label={t("pillar")}>
          <NativeSelect id="so-pillar" {...form.register("pillar")} data-testid="so-pillar">
            <option value="">{t("pillarNone")}</option>
            {pillars.map((p) => <option key={p} value={p}>{tp(p)}</option>)}
          </NativeSelect>
        </Field>
        <Field id="so-owner" required label={te("owner")} error={e.owner_id?.message}>
          <NativeSelect id="so-owner" {...form.register("owner_id")} data-testid="so-owner">{owners.map((o) => <option key={o.id} value={o.id}>{o.label}</option>)}</NativeSelect>
        </Field>
      </div>
      <DepartmentSelect form={form} id="so-department" caps={caps} />
    </Shell>
  );
}

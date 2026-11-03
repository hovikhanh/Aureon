"use client";
/**
 * KPI / OKR editors (SCR-41 "Tạo KPI" · "Tạo Objective", SCR-58/59 "Sửa" · "Lưu trữ" · "Thêm Key Result"):
 * EP-KPI-02/04/05 and EP-OKR-02/04/05/07/09/10 against the real API. Permission is enforced by the API
 * (`execution:write`, not EMP, scope); the UI only hides what the role cannot do (`caps.canManage`).
 */
import * as React from "react";
import { useForm, type FieldValues, type Path, type UseFormReturn } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";
import { Field } from "@/features/admin/common";
import { useDepartments } from "@/features/admin/org/use-org";
import { apiRequest } from "@/lib/api-client";
import { qk } from "@/lib/query-keys";
import type { GoalCaps } from "./GoalsShell";
import { useGoalError } from "./common";
import {
  DIRECTIONS, GOAL_STATUSES, keyResultSchema, kpiSchema, OBJECTIVE_LEVELS, objectiveSchema, OKR_TYPES, ownerOptions, PERIOD_TYPES,
  toKeyResultCreate, toKeyResultUpdate, toKpiCreate, toKpiUpdate, toObjectiveCreate, toObjectiveUpdate, VALUE_TYPES,
  type KeyResultValues, type KpiValues, type ObjectiveValues,
} from "./goal-forms";
import {
  archiveKeyResult, archiveKpi, archiveObjective, createKeyResult, createKpi, createObjective, updateKeyResult, updateKpi,
  updateObjective, useGoalMutation, type KeyResultOut, type KpiOut, type ObjectiveOut,
} from "./use-goals";

type Open = { open: boolean; onOpenChange: (o: boolean) => void };

function useMessages() {
  const t = useTranslations("goals.editor");
  return React.useMemo(() => ({ required: t("required"), number: t("number"), tooLong: t("tooLong"), periodInvalid: t("periodInvalid"), codeInvalid: t("codeInvalid") }), [t]);
}

/** Owner select: CEO/ADM (`platform:read`) choose any active user via EP-ADM `/platform/users`; others own what they create. */
function useOwners(caps: GoalCaps, current?: string | null) {
  const t = useTranslations("goals.editor");
  const users = useQuery({
    queryKey: qk.users({ purpose: "goal-owner" }),
    enabled: caps.canPickOwner,
    queryFn: () => apiRequest<{ id: string; full_name: string; email: string; is_active: boolean }[]>("/platform/users", { query: { limit: 100 } }).then((r) => r.data),
    staleTime: 300_000,
  });
  return ownerOptions({ id: caps.userId, label: t("ownerSelf") }, users.data, caps.canPickOwner, current);
}

/**
 * Department select (CEO/DIR, `hr:read`): options from the existing `/hr/departments` (no new directory
 * endpoint). Empty = company level for the CEO, own department for a DIR; the API rejects a department
 * outside the caller's scope (`403 FORBIDDEN_SCOPE`, shown in place). Hidden for other roles.
 */
function DepartmentSelect<F extends FieldValues>({ form, id, caps }: { form: UseFormReturn<F>; id: string; caps: GoalCaps }) {
  const t = useTranslations("goals.editor");
  const depts = useDepartments();
  if (!caps.canFilterDepartment) return null;
  return (
    <Field id={id} label={t("department")}>
      <NativeSelect id={id} {...form.register("department_id" as Path<F>)} data-testid={id}>
        <option value="">{t(caps.companyWide ? "departmentCompany" : "departmentOwn")}</option>
        {(depts.data?.data ?? []).map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
      </NativeSelect>
    </Field>
  );
}

function Select<F extends FieldValues>({ form, name, id, label, values, tKey }: { form: UseFormReturn<F>; name: Path<F>; id: string; label: string; values: readonly string[]; tKey: string }) {
  const t = useTranslations("goals.editor");
  return (
    <Field id={id} label={label}>
      <NativeSelect id={id} {...form.register(name)} data-testid={id}>
        {values.map((v) => <option key={v} value={v}>{t(`${tKey}.${v}` as "status.draft")}</option>)}
      </NativeSelect>
    </Field>
  );
}

function Shell({ open, onOpenChange, title, testId, error, pending, onSubmit, children }: Open & {
  title: string; testId: string; error: string | null; pending: boolean; onSubmit: (e: React.FormEvent) => void; children: React.ReactNode;
}) {
  const t = useTranslations("goals.form");
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg" data-testid={testId}>
        <DialogTitle>{title}</DialogTitle>
        <DialogDescription className="sr-only">{title}</DialogDescription>
        <form onSubmit={onSubmit} className="mt-4 flex flex-col gap-3" noValidate>
          {children}
          {error && <p role="alert" className="text-sm text-danger" data-testid={`${testId}-error`}>{error}</p>}
          <div className="flex justify-end gap-2">
            <DialogClose asChild><Button type="button" variant="ghost">{t("cancel")}</Button></DialogClose>
            <Button type="submit" disabled={pending} data-testid={`${testId}-submit`}>{t("save")}</Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------------------- KPI
export function KpiEditorDialog({ open, onOpenChange, caps, kpi }: Open & { caps: GoalCaps; kpi?: KpiOut }) {
  const t = useTranslations("goals.editor");
  const toast = useToast();
  const router = useRouter();
  const errText = useGoalError();
  const msgs = useMessages();
  const creating = !kpi;
  const blank = React.useMemo<KpiValues>(() => kpi
    ? { code: kpi.code, name: kpi.name, unit: kpi.unit, target: String(kpi.target), period_type: kpi.period_type as KpiValues["period_type"],
        direction: kpi.direction as KpiValues["direction"], value_type: kpi.value_type as KpiValues["value_type"], status: kpi.status as KpiValues["status"], owner_id: kpi.owner_id, department_id: kpi.department_id ?? "" }
    : { code: "", name: "", unit: "", target: "", period_type: "MONTH", direction: "HIGHER_IS_BETTER", value_type: "numeric", status: "active", owner_id: caps.userId, department_id: "" }, [kpi, caps.userId]);
  const form = useForm<KpiValues>({ resolver: zodResolver(kpiSchema(msgs, { creating })), defaultValues: blank });
  const [error, setError] = React.useState<string | null>(null);
  React.useEffect(() => { if (open) { form.reset(blank); setError(null); } }, [open, form, blank]);
  const owners = useOwners(caps, kpi?.owner_id);
  const m = useGoalMutation((v: KpiValues) => (kpi ? updateKpi(kpi.id, toKpiUpdate(v, kpi.version, kpi.department_id)) : createKpi(toKpiCreate(v))));
  const e = form.formState.errors;
  const submit = form.handleSubmit(async (v) => {
    setError(null);
    try {
      const out = await m.mutateAsync(v);
      toast.push(t(creating ? "kpiCreated" : "kpiUpdated", { code: out.code }));
      onOpenChange(false);
      if (creating) router.push(`/goals/kpis/${out.id}`);
    } catch (err) { setError(errText(err)); }
  });
  return (
    <Shell open={open} onOpenChange={onOpenChange} title={t(creating ? "createKpi" : "editKpi")} testId="kpi-editor" error={error} pending={m.isPending} onSubmit={(ev) => void submit(ev)}>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field id="ke-code" label={t("code")} error={e.code?.message}><Input id="ke-code" {...form.register("code")} disabled={!creating} data-testid="ke-code" /></Field>
        <Field id="ke-unit" label={t("unit")} error={e.unit?.message}><Input id="ke-unit" {...form.register("unit")} data-testid="ke-unit" /></Field>
      </div>
      <Field id="ke-name" label={t("name")} error={e.name?.message}><Input id="ke-name" {...form.register("name")} data-testid="ke-name" /></Field>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field id="ke-target" label={t("target")} error={e.target?.message}><Input id="ke-target" inputMode="decimal" {...form.register("target")} data-testid="ke-target" /></Field>
        {creating
          ? <Select form={form} name="period_type" id="ke-period-type" label={t("periodType")} values={PERIOD_TYPES} tKey="periodTypes" />
          : <Field id="ke-period-type" label={t("periodType")}><Input id="ke-period-type" value={t(`periodTypes.${kpi.period_type}` as "periodTypes.MONTH")} disabled readOnly /></Field>}
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <Select form={form} name="direction" id="ke-direction" label={t("direction")} values={DIRECTIONS} tKey="directions" />
        <Select form={form} name="value_type" id="ke-value-type" label={t("valueType")} values={VALUE_TYPES} tKey="valueTypes" />
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <Select form={form} name="status" id="ke-status" label={t("statusLabel")} values={GOAL_STATUSES} tKey="status" />
        <Field id="ke-owner" label={t("owner")} error={e.owner_id?.message}>
          <NativeSelect id="ke-owner" {...form.register("owner_id")} data-testid="ke-owner">{owners.map((o) => <option key={o.id} value={o.id}>{o.label}</option>)}</NativeSelect>
        </Field>
      </div>
      <DepartmentSelect form={form} id="ke-department" caps={caps} />
    </Shell>
  );
}

// ---------------------------------------------------------------------------------- Objective
export function ObjectiveEditorDialog({ open, onOpenChange, caps, objective, defaultPeriod }: Open & { caps: GoalCaps; objective?: ObjectiveOut; defaultPeriod: string }) {
  const t = useTranslations("goals.editor");
  const toast = useToast();
  const router = useRouter();
  const errText = useGoalError();
  const msgs = useMessages();
  const creating = !objective;
  const blank = React.useMemo<ObjectiveValues>(() => objective
    ? { title: objective.title, period_key: objective.period_key, level: objective.level as ObjectiveValues["level"], okr_type: objective.okr_type as ObjectiveValues["okr_type"],
        status: objective.status as ObjectiveValues["status"], owner_id: objective.owner_id, department_id: objective.department_id ?? "" }
    : { title: "", period_key: defaultPeriod, level: "company", okr_type: "committed", status: "draft", owner_id: caps.userId, department_id: "" }, [objective, caps.userId, defaultPeriod]);
  const form = useForm<ObjectiveValues>({ resolver: zodResolver(objectiveSchema(msgs)), defaultValues: blank });
  const [error, setError] = React.useState<string | null>(null);
  React.useEffect(() => { if (open) { form.reset(blank); setError(null); } }, [open, form, blank]);
  const owners = useOwners(caps, objective?.owner_id);
  const m = useGoalMutation((v: ObjectiveValues) => (objective ? updateObjective(objective.id, toObjectiveUpdate(v, objective.version, objective.department_id)) : createObjective(toObjectiveCreate(v))));
  const e = form.formState.errors;
  const submit = form.handleSubmit(async (v) => {
    setError(null);
    try {
      const out = await m.mutateAsync(v);
      toast.push(t(creating ? "objectiveCreated" : "objectiveUpdated"));
      onOpenChange(false);
      if (creating) router.push(`/goals/objectives/${out.id}`);
    } catch (err) { setError(errText(err)); }
  });
  return (
    <Shell open={open} onOpenChange={onOpenChange} title={t(creating ? "createObjective" : "editObjective")} testId="objective-editor" error={error} pending={m.isPending} onSubmit={(ev) => void submit(ev)}>
      <Field id="oe-title" label={t("title")} error={e.title?.message}><Input id="oe-title" {...form.register("title")} data-testid="oe-title" /></Field>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field id="oe-period" label={t("period")} error={e.period_key?.message}><Input id="oe-period" placeholder="2026-Q4" {...form.register("period_key")} data-testid="oe-period" /></Field>
        <Select form={form} name="level" id="oe-level" label={t("level")} values={OBJECTIVE_LEVELS} tKey="levels" />
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <Select form={form} name="okr_type" id="oe-type" label={t("okrType")} values={OKR_TYPES} tKey="okrTypes" />
        <Select form={form} name="status" id="oe-status" label={t("statusLabel")} values={GOAL_STATUSES} tKey="status" />
      </div>
      <Field id="oe-owner" label={t("owner")} error={e.owner_id?.message}>
        <NativeSelect id="oe-owner" {...form.register("owner_id")} data-testid="oe-owner">{owners.map((o) => <option key={o.id} value={o.id}>{o.label}</option>)}</NativeSelect>
      </Field>
      <DepartmentSelect form={form} id="oe-department" caps={caps} />
      {creating && <p className="text-xs text-muted-foreground">{t("activateHint")}</p>}
    </Shell>
  );
}

// --------------------------------------------------------------------------------- Key result
export function KeyResultEditorDialog({ open, onOpenChange, caps, objectiveId, kr }: Open & { caps: GoalCaps; objectiveId: string; kr?: KeyResultOut }) {
  const t = useTranslations("goals.editor");
  const toast = useToast();
  const errText = useGoalError();
  const msgs = useMessages();
  const creating = !kr;
  const blank = React.useMemo<KeyResultValues>(() => kr
    ? { title: kr.title, baseline: String(kr.baseline), target: String(kr.target), unit: kr.unit, status: kr.status as KeyResultValues["status"], owner_id: kr.owner_id }
    : { title: "", baseline: "0", target: "", unit: "", status: "active", owner_id: caps.userId }, [kr, caps.userId]);
  const form = useForm<KeyResultValues>({ resolver: zodResolver(keyResultSchema(msgs)), defaultValues: blank });
  const [error, setError] = React.useState<string | null>(null);
  React.useEffect(() => { if (open) { form.reset(blank); setError(null); } }, [open, form, blank]);
  const owners = useOwners(caps, kr?.owner_id);
  const m = useGoalMutation((v: KeyResultValues) => (kr ? updateKeyResult(kr.id, toKeyResultUpdate(v, kr.version)) : createKeyResult(objectiveId, toKeyResultCreate(v))));
  const e = form.formState.errors;
  const submit = form.handleSubmit(async (v) => {
    setError(null);
    try { await m.mutateAsync(v); toast.push(t(creating ? "krCreated" : "krUpdated")); onOpenChange(false); } catch (err) { setError(errText(err)); }
  });
  return (
    <Shell open={open} onOpenChange={onOpenChange} title={t(creating ? "createKr" : "editKr")} testId="kr-editor" error={error} pending={m.isPending} onSubmit={(ev) => void submit(ev)}>
      <Field id="re-title" label={t("title")} error={e.title?.message}><Input id="re-title" {...form.register("title")} data-testid="re-title" /></Field>
      <div className="grid gap-3 sm:grid-cols-3">
        <Field id="re-baseline" label={t("baseline")} error={e.baseline?.message}><Input id="re-baseline" inputMode="decimal" {...form.register("baseline")} data-testid="re-baseline" /></Field>
        <Field id="re-target" label={t("target")} error={e.target?.message}><Input id="re-target" inputMode="decimal" {...form.register("target")} data-testid="re-target" /></Field>
        <Field id="re-unit" label={t("unit")} error={e.unit?.message}><Input id="re-unit" {...form.register("unit")} data-testid="re-unit" /></Field>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <Select form={form} name="status" id="re-status" label={t("statusLabel")} values={GOAL_STATUSES} tKey="status" />
        <Field id="re-owner" label={t("owner")} error={e.owner_id?.message}>
          <NativeSelect id="re-owner" {...form.register("owner_id")} data-testid="re-owner">{owners.map((o) => <option key={o.id} value={o.id}>{o.label}</option>)}</NativeSelect>
        </Field>
      </div>
      <p className="text-xs text-muted-foreground">{t("progressHint")}</p>
    </Shell>
  );
}

// ------------------------------------------------------------------------------------ Archive
type ArchiveKind = "kpi" | "objective" | "kr";
const ARCHIVE: Record<ArchiveKind, (id: string) => Promise<void>> = { kpi: archiveKpi, objective: archiveObjective, kr: archiveKeyResult };

/** "Lưu trữ" = soft delete via DELETE (05: `deleted_at`, history kept); still linked → `409` shown in place. */
export function ArchiveDialog({ open, onOpenChange, kind, id, name, after }: Open & { kind: ArchiveKind; id: string; name: string; after?: string }) {
  const t = useTranslations("goals.editor");
  const toast = useToast();
  const router = useRouter();
  const errText = useGoalError();
  const [error, setError] = React.useState<string | null>(null);
  React.useEffect(() => { if (open) setError(null); }, [open]);
  const m = useGoalMutation(() => ARCHIVE[kind](id));
  const confirm = async () => {
    setError(null);
    try { await m.mutateAsync(undefined); toast.push(t("archived", { name })); onOpenChange(false); if (after) router.push(after); } catch (err) { setError(errText(err)); }
  };
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="archive-dialog">
        <DialogTitle>{t(`archive.${kind}` as "archive.kpi")}</DialogTitle>
        <DialogDescription>{t("archiveConfirm", { name })}</DialogDescription>
        {error && <p role="alert" className="text-sm text-danger" data-testid="archive-error">{error}</p>}
        <div className="mt-4 flex justify-end gap-2">
          <DialogClose asChild><Button type="button" variant="ghost">{t("cancel")}</Button></DialogClose>
          <Button type="button" variant="danger" disabled={m.isPending} onClick={() => void confirm()} data-testid="archive-confirm">{t("archiveAction")}</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

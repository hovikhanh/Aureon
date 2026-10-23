"use client";
/** SCR-51 dialogs (T-617F): department create/edit (EP-ORG-07/09), team create (EP-ORG-12), assign/transfer (EP-ORG-22). */
import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useTranslations } from "next-intl";
import { apiRequest } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";
import { Field, useErrorText } from "../common";
import { parentCandidates } from "./org-tree";
import { todayIso, useOrgMutation, usePositions, useTeams, type TreeDept, type TreeMember } from "./use-org";

const CODE = /^[A-Za-z0-9][A-Za-z0-9_-]{0,49}$/;

function FormDialog({ open, onOpenChange, title, testId, busy, error, onSubmit, children }: {
  open: boolean; onOpenChange: (o: boolean) => void; title: string; testId: string; busy: boolean; error: string | null;
  onSubmit: (e: React.FormEvent) => void; children: React.ReactNode;
}) {
  const t = useTranslations();
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid={testId}>
        <DialogTitle>{title}</DialogTitle>
        <DialogDescription className="sr-only">{title}</DialogDescription>
        <form onSubmit={onSubmit} className="mt-4 flex flex-col gap-3" noValidate>
          {children}
          {error && <p role="alert" className="text-sm text-danger" data-testid={`${testId}-error`}>{error}</p>}
          <div className="mt-2 flex justify-end gap-2">
            <DialogClose asChild><Button type="button" variant="ghost">{t("buttons.cancel")}</Button></DialogClose>
            <Button type="submit" disabled={busy} data-testid={`${testId}-submit`}>{t("buttons.save")}</Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ---------------------------------------------------------------- department
export function DepartmentDialog({ open, onOpenChange, orgId, departments, members, editing, defaultParent }: {
  open: boolean; onOpenChange: (o: boolean) => void; orgId: string; departments: TreeDept[]; members: TreeMember[];
  editing?: (TreeDept & { version?: number }) | null; defaultParent?: string | null;
}) {
  const t = useTranslations();
  const toast = useToast();
  const errText = useErrorText();
  const schema = React.useMemo(() => z.object({
    code: z.string().trim().regex(CODE, t("orgAdmin.form.codeInvalid")),
    name: z.string().trim().min(1, t("orgAdmin.form.required")).max(200),
    parent_id: z.string(),
    manager_id: z.string(),
    valid_from: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, t("orgAdmin.form.dateInvalid")),
  }), [t]);
  type V = z.infer<typeof schema>;
  const form = useForm<V>({ resolver: zodResolver(schema) });
  React.useEffect(() => {
    if (open) form.reset({ code: editing?.code ?? "", name: editing?.name ?? "", parent_id: editing?.parent_id ?? defaultParent ?? "", manager_id: editing?.manager_id ?? "", valid_from: todayIso() });
  }, [open, editing, defaultParent, form]);
  const save = useOrgMutation((v: V) => editing
    ? apiRequest(`/hr/departments/${editing.id}`, { method: "PATCH", body: { code: v.code, name: v.name, parent_id: v.parent_id || null, manager_id: v.manager_id || null } })
    : apiRequest("/hr/departments", { method: "POST", idempotent: true, body: { organization_id: orgId, code: v.code, name: v.name, parent_id: v.parent_id || null, manager_id: v.manager_id || null, valid_from: v.valid_from } }));
  const submit = form.handleSubmit(async (v) => {
    await save.mutateAsync(v);
    toast.push(t(editing ? "orgAdmin.toast.deptUpdated" : "orgAdmin.toast.deptCreated", { name: v.name }));
    onOpenChange(false);
  });
  const e = form.formState.errors;
  const parents = parentCandidates(departments, editing?.id ?? null);
  return (
    <FormDialog open={open} onOpenChange={(o) => { save.reset(); onOpenChange(o); }} title={t(editing ? "orgAdmin.form.editDept" : "orgAdmin.form.newDept")} testId="dept-form"
      busy={save.isPending} error={save.isError ? errText(save.error) : null} onSubmit={(ev) => void submit(ev)}>
      <Field id="dept-code" label={t("orgAdmin.form.code")} error={e.code?.message}><Input id="dept-code" {...form.register("code")} aria-invalid={Boolean(e.code)} data-testid="dept-code" /></Field>
      <Field id="dept-name" label={t("orgAdmin.form.name")} error={e.name?.message}><Input id="dept-name" {...form.register("name")} aria-invalid={Boolean(e.name)} data-testid="dept-name" /></Field>
      <Field id="dept-parent" label={t("orgAdmin.form.parent")}>
        <NativeSelect id="dept-parent" {...form.register("parent_id")} data-testid="dept-parent">
          <option value="">{t("orgAdmin.form.noParent")}</option>
          {parents.map((d) => <option key={d.id} value={d.id}>{d.code} — {d.name}</option>)}
        </NativeSelect>
      </Field>
      <Field id="dept-manager" label={t("orgAdmin.form.head")}>
        <NativeSelect id="dept-manager" {...form.register("manager_id")} data-testid="dept-manager">
          <option value="">{t("common.none")}</option>
          {members.map((m) => <option key={m.employee_id} value={m.employee_id}>{m.employee_code} — {m.full_name}</option>)}
        </NativeSelect>
      </Field>
      {!editing && <Field id="dept-from" label={t("orgAdmin.form.validFrom")} error={e.valid_from?.message}><Input id="dept-from" type="date" {...form.register("valid_from")} data-testid="dept-from" /></Field>}
    </FormDialog>
  );
}

// ---------------------------------------------------------------- team
export function TeamDialog({ open, onOpenChange, department }: { open: boolean; onOpenChange: (o: boolean) => void; department: TreeDept | null }) {
  const t = useTranslations();
  const toast = useToast();
  const errText = useErrorText();
  const schema = React.useMemo(() => z.object({
    code: z.string().trim().regex(CODE, t("orgAdmin.form.codeInvalid")),
    name: z.string().trim().min(1, t("orgAdmin.form.required")).max(200),
    lead_employee_id: z.string(),
  }), [t]);
  type V = z.infer<typeof schema>;
  const form = useForm<V>({ resolver: zodResolver(schema) });
  React.useEffect(() => { if (open) form.reset({ code: department ? `${department.code}-` : "", name: "", lead_employee_id: "" }); }, [open, department, form]);
  const save = useOrgMutation((v: V) => apiRequest("/org/teams", { method: "POST", idempotent: true, body: { department_id: department?.id, code: v.code, name: v.name, lead_employee_id: v.lead_employee_id || null } }));
  const submit = form.handleSubmit(async (v) => {
    await save.mutateAsync(v);
    toast.push(t("orgAdmin.toast.teamCreated", { name: v.name }));
    onOpenChange(false);
  });
  const e = form.formState.errors;
  return (
    <FormDialog open={open} onOpenChange={(o) => { save.reset(); onOpenChange(o); }} title={t("orgAdmin.form.newTeam", { dept: department?.name ?? "" })} testId="team-form"
      busy={save.isPending} error={save.isError ? errText(save.error) : null} onSubmit={(ev) => void submit(ev)}>
      <Field id="team-code" label={t("orgAdmin.form.code")} error={e.code?.message}><Input id="team-code" {...form.register("code")} data-testid="team-code" /></Field>
      <Field id="team-name" label={t("orgAdmin.form.name")} error={e.name?.message}><Input id="team-name" {...form.register("name")} data-testid="team-name" /></Field>
      <Field id="team-lead" label={t("orgAdmin.form.lead")}>
        <NativeSelect id="team-lead" {...form.register("lead_employee_id")} data-testid="team-lead">
          <option value="">{t("common.none")}</option>
          {department?.members.map((m) => <option key={m.employee_id} value={m.employee_id}>{m.employee_code} — {m.full_name}</option>)}
        </NativeSelect>
      </Field>
    </FormDialog>
  );
}

// ---------------------------------------------------------------- assign / transfer
export function AssignDialog({ open, onOpenChange, departments, employees, employee, defaultDept }: {
  open: boolean; onOpenChange: (o: boolean) => void; departments: TreeDept[]; employees: TreeMember[];
  employee?: TreeMember | null; defaultDept?: string | null;
}) {
  const t = useTranslations();
  const toast = useToast();
  const errText = useErrorText();
  const today = todayIso();
  const schema = React.useMemo(() => z.object({
    employee_id: z.string().min(1, t("orgAdmin.form.required")),
    department_id: z.string().min(1, t("orgAdmin.form.required")),
    team_id: z.string(),
    position_id: z.string(),
    manager_id: z.string(),
    valid_from: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, t("orgAdmin.form.dateInvalid")).refine((v) => v <= today, t("orgAdmin.form.notFuture")),
    reason: z.string().max(500),
  }).refine((v) => v.manager_id !== v.employee_id, { path: ["manager_id"], message: t("adminCommon.reason.manager_self") }), [t, today]);
  type V = z.infer<typeof schema>;
  const form = useForm<V>({ resolver: zodResolver(schema) });
  React.useEffect(() => {
    if (open) form.reset({ employee_id: employee?.employee_id ?? "", department_id: defaultDept ?? "", team_id: "", position_id: "", manager_id: "", valid_from: today, reason: "" });
  }, [open, employee, defaultDept, today, form]);
  const dept = form.watch("department_id");
  const teams = useTeams(dept || null);
  const positions = usePositions(dept || null);
  const save = useOrgMutation((v: V) => apiRequest("/org/assignments", { method: "POST", idempotent: true, body: {
    employee_id: v.employee_id, department_id: v.department_id, team_id: v.team_id || null, position_id: v.position_id || null,
    manager_id: v.manager_id || null, valid_from: v.valid_from, reason: v.reason.trim() || null } }));
  const submit = form.handleSubmit(async (v) => {
    await save.mutateAsync(v);
    toast.push(t("orgAdmin.toast.assigned"));
    onOpenChange(false);
  });
  const e = form.formState.errors;
  return (
    <FormDialog open={open} onOpenChange={(o) => { save.reset(); onOpenChange(o); }} title={t(employee ? "orgAdmin.form.transfer" : "orgAdmin.form.assign", { name: employee?.full_name ?? "" })}
      testId="assign-form" busy={save.isPending} error={save.isError ? errText(save.error) : null} onSubmit={(ev) => void submit(ev)}>
      {!employee && (
        <Field id="as-emp" label={t("orgAdmin.form.employee")} error={e.employee_id?.message}>
          <NativeSelect id="as-emp" {...form.register("employee_id")} data-testid="assign-employee">
            <option value="">{t("orgAdmin.form.pick")}</option>
            {employees.map((m) => <option key={m.employee_id} value={m.employee_id}>{m.employee_code} — {m.full_name}</option>)}
          </NativeSelect>
        </Field>
      )}
      <Field id="as-dept" label={t("orgAdmin.form.department")} error={e.department_id?.message}>
        <NativeSelect id="as-dept" {...form.register("department_id", { onChange: () => { form.setValue("team_id", ""); form.setValue("position_id", ""); } })} data-testid="assign-dept">
          <option value="">{t("orgAdmin.form.pick")}</option>
          {departments.map((d) => <option key={d.id} value={d.id}>{d.code} — {d.name}</option>)}
        </NativeSelect>
      </Field>
      <div className="grid grid-cols-2 gap-3">
        <Field id="as-team" label={t("orgAdmin.form.team")}>
          <NativeSelect id="as-team" {...form.register("team_id")} disabled={!dept} data-testid="assign-team">
            <option value="">{t("common.none")}</option>
            {(teams.data?.data ?? []).map((x) => <option key={x.id} value={x.id}>{x.code} — {x.name}</option>)}
          </NativeSelect>
        </Field>
        <Field id="as-pos" label={t("orgAdmin.form.position")}>
          <NativeSelect id="as-pos" {...form.register("position_id")} disabled={!dept} data-testid="assign-position">
            <option value="">{t("common.none")}</option>
            {(positions.data?.data ?? []).map((x) => <option key={x.id} value={x.id}>{x.code} — {x.title}</option>)}
          </NativeSelect>
        </Field>
      </div>
      <Field id="as-mgr" label={t("orgAdmin.form.manager")} error={e.manager_id?.message}>
        <NativeSelect id="as-mgr" {...form.register("manager_id")} data-testid="assign-manager">
          <option value="">{t("common.none")}</option>
          {employees.map((m) => <option key={m.employee_id} value={m.employee_id}>{m.employee_code} — {m.full_name}</option>)}
        </NativeSelect>
      </Field>
      <Field id="as-from" label={t("orgAdmin.form.effectiveFrom")} error={e.valid_from?.message}>
        <Input id="as-from" type="date" max={today} {...form.register("valid_from")} aria-invalid={Boolean(e.valid_from)} data-testid="assign-from" />
      </Field>
      <Field id="as-reason" label={t("orgAdmin.form.reason")}><Input id="as-reason" {...form.register("reason")} data-testid="assign-reason" /></Field>
    </FormDialog>
  );
}

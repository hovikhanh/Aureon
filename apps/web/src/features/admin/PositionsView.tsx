"use client";
/** SCR-52 `/admin/positions` (T-617F, FR-ORG-06): positions by department with budget / filled / vacant + create/edit (rhf + zod). */
import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useTranslations } from "next-intl";
import { apiRequest } from "@/lib/api-client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";
import { AdminHeader, Field, useErrorText } from "./common";
import { useDepartments, useOrgMutation, usePositions, type PositionOut } from "./org/use-org";

export function PositionsView({ canEdit }: { canEdit: boolean }) {
  const t = useTranslations();
  const [dept, setDept] = React.useState("");
  const [q, setQ] = React.useState("");
  const [editing, setEditing] = React.useState<PositionOut | "new" | null>(null);
  const depts = useDepartments();
  const positions = usePositions(dept || null, q);
  const deptName = (id: string) => depts.data?.data.find((d) => d.id === id)?.name ?? "—";
  const rows = positions.data?.data ?? [];
  return (
    <div className="mx-auto flex max-w-[1400px] flex-col gap-4" data-testid="positions-admin">
      <AdminHeader title={t("positionsAdmin.title")} hint={t("positionsAdmin.hint")}>
        {canEdit && <Button size="sm" onClick={() => setEditing("new")} data-testid="position-new">{t("positionsAdmin.new")}</Button>}
      </AdminHeader>
      <div className="flex flex-wrap gap-2">
        <NativeSelect aria-label={t("positionsAdmin.filterDept")} value={dept} onChange={(e) => setDept(e.target.value)} data-testid="position-filter-dept">
          <option value="">{t("positionsAdmin.allDepts")}</option>
          {(depts.data?.data ?? []).map((d) => <option key={d.id} value={d.id}>{d.code} — {d.name}</option>)}
        </NativeSelect>
        <Input className="max-w-xs" placeholder={t("positionsAdmin.search")} aria-label={t("positionsAdmin.search")} value={q} onChange={(e) => setQ(e.target.value)} data-testid="position-search" />
      </div>
      {positions.isPending && <div className="h-40 animate-pulse rounded-lg bg-muted" />}
      {positions.isError && <p role="alert" className="text-danger">{t("errors.generic")}</p>}
      {positions.isSuccess && !rows.length && <p className="text-muted-foreground" data-testid="positions-empty">{t("positionsAdmin.empty")}</p>}
      {rows.length > 0 && (
        <Card className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-sm" data-testid="positions-table">
            <thead className="border-b bg-muted/50 text-left text-xs text-muted-foreground">
              <tr>{(["code", "title", "department", "level", "budget", "filled", "vacant"] as const).map((c) => <th key={c} scope="col" className="px-3 py-2 font-medium">{t(`positionsAdmin.col.${c}`)}</th>)}{canEdit && <th className="px-3 py-2"><span className="sr-only">{t("orgAdmin.edit")}</span></th>}</tr>
            </thead>
            <tbody className="divide-y">
              {rows.map((p) => (
                <tr key={p.id} data-testid="position-row" data-code={p.code}>
                  <td className="px-3 py-2 font-mono">{p.code}</td>
                  <td className="px-3 py-2">{p.title}</td>
                  <td className="px-3 py-2">{deptName(p.department_id)}</td>
                  <td className="px-3 py-2 tabular-nums">{p.level ?? "—"}</td>
                  <td className="px-3 py-2 tabular-nums">{p.headcount_budget}</td>
                  <td className="px-3 py-2 tabular-nums">{p.filled}</td>
                  <td className="px-3 py-2"><Badge variant={p.vacant > 0 ? "warning" : "success"} className="tabular-nums" data-testid="position-vacant">{p.vacant}</Badge></td>
                  {canEdit && <td className="px-3 py-2 text-right"><Button size="sm" variant="ghost" onClick={() => setEditing(p)} data-testid="position-edit">{t("orgAdmin.edit")}</Button></td>}
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
      {canEdit && <PositionDialog editing={editing} onClose={() => setEditing(null)} departments={depts.data?.data ?? []} positions={rows} />}
    </div>
  );
}

function PositionDialog({ editing, onClose, departments, positions }: { editing: PositionOut | "new" | null; onClose: () => void; departments: { id: string; code: string; name: string }[]; positions: PositionOut[] }) {
  const t = useTranslations();
  const toast = useToast();
  const errText = useErrorText();
  const current = editing && editing !== "new" ? editing : null;
  const schema = React.useMemo(() => z.object({
    department_id: z.string().min(1, t("orgAdmin.form.required")),
    code: z.string().trim().regex(/^[A-Za-z0-9][A-Za-z0-9_-]{0,49}$/, t("orgAdmin.form.codeInvalid")),
    title: z.string().trim().min(1, t("orgAdmin.form.required")).max(200),
    level: z.string().regex(/^\d{0,4}$/, t("positionsAdmin.levelInvalid")),
    headcount_budget: z.coerce.number<string>().int(t("positionsAdmin.budgetInvalid")).min(0, t("positionsAdmin.budgetInvalid")).max(32767),
    reports_to_position_id: z.string(),
  }), [t]);
  type In = z.input<typeof schema>;
  type V = z.output<typeof schema>;
  const form = useForm<In, unknown, V>({ resolver: zodResolver(schema) });
  React.useEffect(() => {
    if (editing) form.reset({ department_id: current?.department_id ?? "", code: current?.code ?? "", title: current?.title ?? "", level: current?.level?.toString() ?? "",
      headcount_budget: String(current?.headcount_budget ?? 1), reports_to_position_id: current?.reports_to_position_id ?? "" });
  }, [editing, current, form]);
  const save = useOrgMutation((v: V) => {
    const common = { title: v.title, level: v.level ? Number(v.level) : null, headcount_budget: v.headcount_budget, reports_to_position_id: v.reports_to_position_id || null };
    return current
      ? apiRequest(`/org/positions/${current.id}`, { method: "PATCH", body: { ...common, version: current.version } })
      : apiRequest("/org/positions", { method: "POST", idempotent: true, body: { ...common, department_id: v.department_id, code: v.code } });
  });
  const submit = form.handleSubmit(async (v) => {
    await save.mutateAsync(v);
    toast.push(t(current ? "positionsAdmin.updated" : "positionsAdmin.created", { title: v.title }));
    onClose();
  });
  const e = form.formState.errors;
  return (
    <Dialog open={editing !== null} onOpenChange={(o) => { if (!o) { save.reset(); onClose(); } }}>
      <DialogContent data-testid="position-form">
        <DialogTitle>{t(current ? "positionsAdmin.edit" : "positionsAdmin.new")}</DialogTitle>
        <DialogDescription className="sr-only">{t("positionsAdmin.hint")}</DialogDescription>
        <form onSubmit={(ev) => void submit(ev)} className="mt-4 flex flex-col gap-3" noValidate>
          <Field id="pos-dept" label={t("orgAdmin.form.department")} error={e.department_id?.message}>
            <NativeSelect id="pos-dept" {...form.register("department_id")} disabled={Boolean(current)} data-testid="position-dept">
              <option value="">{t("orgAdmin.form.pick")}</option>
              {departments.map((d) => <option key={d.id} value={d.id}>{d.code} — {d.name}</option>)}
            </NativeSelect>
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field id="pos-code" label={t("orgAdmin.form.code")} error={e.code?.message}><Input id="pos-code" {...form.register("code")} disabled={Boolean(current)} data-testid="position-code" /></Field>
            <Field id="pos-level" label={t("positionsAdmin.col.level")} error={e.level?.message}><Input id="pos-level" inputMode="numeric" {...form.register("level")} data-testid="position-level" /></Field>
          </div>
          <Field id="pos-title" label={t("positionsAdmin.col.title")} error={e.title?.message}><Input id="pos-title" {...form.register("title")} data-testid="position-title" /></Field>
          <Field id="pos-budget" label={t("positionsAdmin.col.budget")} error={e.headcount_budget?.message}><Input id="pos-budget" type="number" min={0} {...form.register("headcount_budget")} data-testid="position-budget" /></Field>
          <Field id="pos-reports" label={t("positionsAdmin.reportsTo")}>
            <NativeSelect id="pos-reports" {...form.register("reports_to_position_id")} data-testid="position-reports">
              <option value="">{t("common.none")}</option>
              {positions.filter((p) => p.id !== current?.id).map((p) => <option key={p.id} value={p.id}>{p.code} — {p.title}</option>)}
            </NativeSelect>
          </Field>
          {save.isError && <p role="alert" className="text-sm text-danger" data-testid="position-form-error">{errText(save.error)}</p>}
          <div className="mt-2 flex justify-end gap-2">
            <DialogClose asChild><Button type="button" variant="ghost">{t("buttons.cancel")}</Button></DialogClose>
            <Button type="submit" disabled={save.isPending} data-testid="position-form-submit">{t("buttons.save")}</Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

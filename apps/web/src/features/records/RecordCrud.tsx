"use client";
/**
 * Generic list + create / edit / archive / row actions for one business-record resource (M7) — the
 * resource is described by `ResourceSpec` (specs.ts), the form by `record-form.ts`. Writes go to
 * the existing API only; permission + scope are enforced there (the UI hides what the role cannot
 * do and shows 403/404 in place — R-DEC-162). "Lưu trữ" = the API's soft DELETE (`deleted_at`).
 */
import * as React from "react";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useFieldArray, useForm, type UseFormReturn } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";
import { QueryError } from "@/components/QueryError";
import { SortHeader } from "@/components/SortHeader";
import { Field } from "@/features/admin/common";
import { ApiError, apiRequest } from "@/lib/api-client";
import { errorText } from "@/lib/error-text";
import { formatDate, formatDateTime, formatMoney, formatNumber, type AppLocale } from "@/lib/format";
import { canAccess } from "@/lib/permissions";
import { nextSort, type SortState } from "@/lib/sort";
import { createBody, emptyLine, initialValues, recordSchema, similarOf, updateBody, VAT_RATES, type FieldSpec, type FormValues, type RefKind, type Similar } from "./record-form";
import { RESOURCES, refKindsOf, type ActionSpec, type ColumnSpec, type ResourceSpec } from "./specs";

type Row = Record<string, unknown> & { id: string; version: number };
type Option = { id: string; label: string };

export interface RecordCaps {
  userId: string;
  role: string;
  scopePillars: readonly string[];
  departmentId: string | null;
  permissions: readonly string[];
  /** `<domain>:write` inside the khối (create / edit / archive / actions). */
  canWrite: boolean;
  /** Which reference lists this role can read (they are khối-isolated, R-DEC-161). */
  canReadDepartments: boolean;
  canReadClients: boolean;
  canReadEmployees: boolean;
  /** `platform:read` (CEO/ADM): pick any user as owner — else the owner is the caller. */
  canPickUser: boolean;
}

const PAGE = 50;

/** Options of a reference picker from the existing list endpoints; `null` = not readable here. */
function useRefOptions(kind: RefKind, caps: RecordCaps, t: (k: string) => string, need = true): Option[] | null {
  const spec = {
    department: { on: caps.canReadDepartments, path: "/hr/departments", query: { limit: 100 }, label: (r: Row) => String(r.name) },
    client: { on: caps.canReadClients, path: "/sales/clients", query: { limit: 100, sort_by: "name", order: "asc" }, label: (r: Row) => String(r.name) },
    employee: { on: caps.canReadEmployees, path: "/hr/employees", query: { limit: 100, sort_by: "full_name", order: "asc" }, label: (r: Row) => `${r.full_name} · ${r.employee_code}` },
    user: { on: caps.canPickUser, path: "/platform/users", query: { limit: 100 }, label: (r: Row) => `${r.full_name} · ${r.email}` },
    product: { on: caps.permissions.includes("product:read"), path: "/product/products", query: { limit: 100, sort_by: "name", order: "asc" }, label: (r: Row) => `${r.code} · ${r.name}` },
    risk: { on: caps.permissions.includes("risk:read"), path: "/risk/risks", query: { limit: 100, sort_by: "code", order: "asc" }, label: (r: Row) => `${r.code} · ${r.title}` },
    // CRM (R-DEC-176): fetched only by the resources that reference them (`need`)
    lead: { on: caps.canReadClients, path: "/sales/leads", query: { limit: 100, sort_by: "updated_at" }, label: (r: Row) => `${r.code} · ${r.full_name}` },
    contact: { on: caps.canReadClients, path: "/sales/contacts", query: { limit: 100, sort_by: "updated_at" }, label: (r: Row) => `${r.full_name} · ${r.code}` },
    deal: { on: caps.canReadClients, path: "/sales/deals", query: { limit: 100, sort_by: "updated_at" }, label: (r: Row) => String(r.name) },
  }[kind];
  const q = useQuery({
    queryKey: ["records", "ref", kind],
    enabled: spec.on && need,
    staleTime: 300_000,
    queryFn: ({ signal }) => apiRequest<Row[]>(spec.path, { query: spec.query, signal }).then((r) => r.data),
  });
  if (spec.on) return (q.data ?? []).map((r) => ({ id: r.id, label: spec.label(r) }));
  if (kind === "user") return [{ id: caps.userId, label: t("me") }];
  if (kind === "department" && caps.departmentId) return [{ id: caps.departmentId, label: t("myDepartment") }];
  return null;
}

function useRefs(caps: RecordCaps, t: (k: string) => string, needed?: ReadonlySet<RefKind>): Record<RefKind, Option[] | null> {
  const need = (k: RefKind) => !needed || needed.has(k);
  return {
    lead: useRefOptions("lead", caps, t, need("lead")),
    contact: useRefOptions("contact", caps, t, need("contact")),
    deal: useRefOptions("deal", caps, t, need("deal")),
    department: useRefOptions("department", caps, t),
    client: useRefOptions("client", caps, t),
    employee: useRefOptions("employee", caps, t),
    user: useRefOptions("user", caps, t),
    product: useRefOptions("product", caps, t),
    risk: useRefOptions("risk", caps, t),
  };
}

/** Optional reference fields the role cannot resolve are left out (the API defaults / pins them). */
const usable = (fields: readonly FieldSpec[], refs: Record<RefKind, Option[] | null>) =>
  fields.filter((f) => f.type !== "ref" || f.required || refs[f.ref!] !== null);

function Cell({ col, row, refs }: { col: ColumnSpec; row: Row; refs: Record<RefKind, Option[] | null> }) {
  const t = useTranslations("records");
  const locale = useLocale() as AppLocale;
  const v = row[col.name];
  if (v === null || v === undefined || v === "") return <>—</>;
  switch (col.type) {
    case "money": return <>{formatMoney(Number(v), locale)}</>;
    case "pct": return <>{formatNumber(Number(v), locale, 0)}%</>;
    case "date": return <>{formatDate(String(v), locale)}</>;
    case "bool": return <>{v ? "✓" : "—"}</>;
    case "datetime": return <>{formatDateTime(String(v), locale)}</>;
    case "list": return <>{Array.isArray(v) && v.length ? v.map((x) => (t.has(`enum.${col.name}.${x}`) ? t(`enum.${col.name}.${x}` as "me") : String(x))).join(", ") : "—"}</>;
    case "enum": return <>{t.has(`enum.${col.name}.${v}`) ? t(`enum.${col.name}.${v}` as "me") : String(v)}</>;
    case "ref": return <>{refs[col.ref!]?.find((o) => o.id === v)?.label ?? t(`other.${col.ref!}` as "me")}</>;
    default: return <>{String(v)}</>;
  }
}

function FieldInput({ f, form, refs, disabled, prefix }: { f: FieldSpec; form: UseFormReturn<FormValues>; refs: Record<RefKind, Option[] | null>; disabled: boolean; prefix: string }) {
  const t = useTranslations("records");
  const id = `${prefix}-${f.name}`;
  const err = form.formState.errors[f.name]?.message as string | undefined;
  const label = `${t(`field.${f.name}` as "me")}${f.required ? " *" : ""}`;
  if (f.type === "lines") return <LinesInput form={form} name={f.name} label={label} disabled={disabled} error={err} />;
  if (f.type === "multi") return <MultiInput f={f} form={form} label={label} disabled={disabled} prefix={id} />;
  if (f.type === "boolean") {
    return (
      <label className="flex items-center gap-2 text-sm" htmlFor={id}>
        <input id={id} type="checkbox" className="h-4 w-4" disabled={disabled} {...form.register(f.name)} data-testid={id} />{label}
      </label>
    );
  }
  let control: React.ReactNode;
  if (f.type === "select" || f.type === "ref") {
    const opts: Option[] = f.type === "ref"
      ? refs[f.ref!] ?? []
      : (f.options ?? []).map((o) => ({ id: o, label: t.has(`enum.${f.name}.${o}`) ? t(`enum.${f.name}.${o}` as "me") : o }));
    control = (
      <NativeSelect id={id} disabled={disabled} {...form.register(f.name)} data-testid={id}>
        <option value="">{f.required ? t("choose") : "—"}</option>
        {opts.map((o) => <option key={o.id} value={o.id}>{o.label}</option>)}
      </NativeSelect>
    );
  } else if (f.type === "textarea") {
    control = <textarea id={id} disabled={disabled} className="min-h-20 w-full rounded border bg-card p-2 text-sm" {...form.register(f.name)} data-testid={id} />;
  } else {
    const type = f.type === "date" ? "date" : f.type === "datetime" ? "datetime-local" : "text";
    const inputMode = ["money", "number", "pct"].includes(f.type) ? "decimal" : undefined;
    const placeholder = f.type === "month" ? "2026-11" : undefined;
    control = <Input id={id} type={type} inputMode={inputMode} placeholder={placeholder} disabled={disabled} {...form.register(f.name)} data-testid={id} />;
  }
  return <Field id={id} label={t(`field.${f.name}` as "me")} error={err} required={f.required}>{control}</Field>;
}

/** Checkbox group over `options` → string[] (e.g. contact roles, R-DEC-176). */
function MultiInput({ f, form, label, disabled, prefix }: { f: FieldSpec; form: UseFormReturn<FormValues>; label: string; disabled: boolean; prefix: string }) {
  const t = useTranslations("records");
  return (
    <fieldset className="flex flex-col gap-1" data-testid={prefix}>
      <legend className="text-sm font-medium">{label}</legend>
      <div className="flex flex-wrap gap-x-4 gap-y-1">
        {(f.options ?? []).map((o) => (
          <label key={o} className="flex items-center gap-1.5 text-sm">
            <input type="checkbox" className="h-4 w-4" value={o} disabled={disabled} {...form.register(f.name)} data-testid={`${prefix}-${o}`} />
            {t.has(`enum.${f.name}.${o}`) ? t(`enum.${f.name}.${o}` as "me") : o}
          </label>
        ))}
      </div>
    </fieldset>
  );
}

function LinesInput({ form, name, label, disabled, error }: { form: UseFormReturn<FormValues>; name: string; label: string; disabled: boolean; error?: string }) {
  const t = useTranslations("records");
  // `lines` is the only array field; react-hook-form types the dynamic name as never
  const arr = useFieldArray({ control: form.control, name: name as never });
  return (
    <fieldset className="flex flex-col gap-2" data-testid={`lines-${name}`}>
      <legend className="text-sm font-medium">{label}</legend>
      {arr.fields.map((line, i) => (
        <div key={line.id} className="grid grid-cols-12 gap-2">
          <Input className="col-span-5" placeholder={t("line.description")} aria-label={t("line.description")} disabled={disabled} {...form.register(`${name}.${i}.description`)} data-testid={`line-${i}-description`} />
          <Input className="col-span-2" inputMode="decimal" aria-label={t("line.quantity")} disabled={disabled} {...form.register(`${name}.${i}.quantity`)} data-testid={`line-${i}-quantity`} />
          <Input className="col-span-3" inputMode="decimal" placeholder={t("line.unitPrice")} aria-label={t("line.unitPrice")} disabled={disabled} {...form.register(`${name}.${i}.unit_price`)} data-testid={`line-${i}-unit_price`} />
          <NativeSelect className="col-span-2" aria-label={t("line.vat")} disabled={disabled} {...form.register(`${name}.${i}.vat_pct`)}>
            {VAT_RATES.map((v) => <option key={v} value={v}>{v}%</option>)}
          </NativeSelect>
        </div>
      ))}
      {!disabled && (
        <div className="flex gap-2">
          <Button type="button" size="sm" variant="outline" onClick={() => arr.append(emptyLine() as never)}>{t("line.add")}</Button>
          {arr.fields.length > 1 && <Button type="button" size="sm" variant="ghost" onClick={() => arr.remove(arr.fields.length - 1)}>{t("line.remove")}</Button>}
        </div>
      )}
      {error && <p className="text-xs text-danger">{error}</p>}
    </fieldset>
  );
}

function useMessages() {
  const t = useTranslations("records.msg");
  return React.useMemo(() => ({ required: t("required"), number: t("number"), tooLong: t("tooLong"), range: t("range"), period: t("period"), lines: t("lines") }), [t]);
}

/** One dialog for create, edit and row actions — all are "a form over a field list, then a request". */
function FormDialog({ open, onClose, title, testId, fields, row, defaults, submit, refs }: {
  open: boolean; onClose: () => void; title: string; testId: string; fields: readonly FieldSpec[]; row?: Row;
  defaults?: Record<string, string | boolean>; submit: (v: FormValues, extra?: Record<string, unknown>) => Promise<unknown>; refs: Record<RefKind, Option[] | null>;
}) {
  const tAll = useTranslations();
  const t = useTranslations("records");
  const msgs = useMessages();
  const schema = React.useMemo(() => recordSchema(fields, msgs), [fields, msgs]);
  const init = React.useMemo(() => initialValues(fields, row, defaults), [fields, row, defaults]);
  const form = useForm<FormValues>({ resolver: zodResolver(schema) as never, defaultValues: init });
  const [error, setError] = React.useState<string | null>(null);
  // R-DEC-176 d: a possible duplicate (same e-mail / phone) is a warning — the user may save anyway
  const [similar, setSimilar] = React.useState<{ list: Similar[]; values: FormValues } | null>(null);
  const [confirming, setConfirming] = React.useState(false);
  // Reset when the dialog opens or the initial values change in CONTENT — not on every new object:
  // the parent re-renders when a background query settles, and resetting then wiped what the user
  // had already typed (seen live on the invoice form).
  const initRef = React.useRef(init);
  initRef.current = init;
  const initKey = JSON.stringify(init);
  React.useEffect(() => { if (open) { form.reset(initRef.current); setError(null); setSimilar(null); } }, [open, initKey, form]);
  const run = async (v: FormValues, extra?: Record<string, unknown>) => {
    setError(null);
    setSimilar(null);
    try { await submit(v, extra); onClose(); } catch (e) {
      const sim = e instanceof ApiError && e.code === "DUPLICATE_RESOURCE" && !extra ? similarOf(e.details) : null;
      if (sim) return setSimilar({ list: sim, values: v });
      // a rule / duplicate / validation answer that names a field is shown on that field (10 §1.4 `details.field`)
      const field = e instanceof ApiError && typeof e.details.field === "string" ? e.details.field : null;
      const known = field && fields.some((f) => f.name === field);
      if (e instanceof ApiError && e.code === "DUPLICATE_RESOURCE") setError(t("msg.duplicate"));
      else if (e instanceof ApiError && e.code === "BUSINESS_RULE_VIOLATION") setError(t("msg.rule"));
      else setError(errorText(tAll, e));
      if (known) form.setError(field, { message: e instanceof ApiError && e.code === "DUPLICATE_RESOURCE" ? t("msg.duplicate") : t("msg.ruleField") });
    }
  };
  const onSubmit = form.handleSubmit((v) => run(v));
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-2xl" data-testid={testId}>
        <DialogTitle>{title}</DialogTitle>
        <DialogDescription className="sr-only">{title}</DialogDescription>
        <form onSubmit={(e) => void onSubmit(e)} className="mt-4 flex flex-col gap-3" noValidate>
          <div className="grid gap-3 sm:grid-cols-2">
            {fields.map((f) => (
              <div key={f.name} className={f.type === "lines" || f.type === "textarea" || f.type === "multi" ? "sm:col-span-2" : undefined}>
                <FieldInput f={f} form={form} refs={refs} disabled={Boolean(row && f.createOnly)} prefix={testId} />
              </div>
            ))}
          </div>
          {error && <p role="alert" className="text-sm text-danger" data-testid={`${testId}-error`}>{error}</p>}
          {similar && (
            <div role="alert" className="rounded border border-warning bg-warning-subtle p-3 text-sm" data-testid={`${testId}-similar`}>
              <p className="font-medium">{t("similar.title")}</p>
              <ul className="mt-1 list-disc pl-5">
                {similar.list.map((x) => <li key={x.id}>{x.code} · {x.name} ({x.match.map((m) => t(`similar.match.${m}` as "me")).join(", ")})</li>)}
              </ul>
              <Button type="button" size="sm" variant="outline" className="mt-2" disabled={confirming}
                onClick={() => { setConfirming(true); void run(similar.values, { confirm_duplicate: true }).finally(() => setConfirming(false)); }} data-testid={`${testId}-confirm-duplicate`}>{t("similar.saveAnyway")}</Button>
            </div>
          )}
          <DialogFooter>
            <DialogClose asChild><Button type="button" variant="ghost">{t("cancel")}</Button></DialogClose>
            <Button type="submit" disabled={form.formState.isSubmitting} data-testid={`${testId}-submit`}>{t("save")}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export function RecordCrud({ spec, caps }: { spec: ResourceSpec; caps: RecordCaps }) {
  const t = useTranslations("records");
  const tAll = useTranslations();
  const toast = useToast();
  const client = useQueryClient();
  const refs = useRefs(caps, (k) => t(k as "me"), React.useMemo(() => refKindsOf(spec), [spec]));
  const [offset, setOffset] = React.useState(0);
  const [q, setQ] = React.useState("");
  const [editing, setEditing] = React.useState<Row | "new" | null>(null);
  const [acting, setActing] = React.useState<{ action: ActionSpec; row: Row } | null>(null);
  const [archiving, setArchiving] = React.useState<Row | null>(null);
  const [sort, setSort] = React.useState<SortState>({ field: spec.sortBy, order: spec.order ?? "desc" });
  const onSort = (field: string) => { setSort(nextSort(sort, field)); setOffset(0); };
  const params = { limit: PAGE, offset, sort_by: sort.field, order: sort.order, q: spec.searchable && q ? q : undefined };
  const list = useQuery({
    queryKey: ["records", spec.path, params],
    queryFn: ({ signal }) => apiRequest<Row[]>(spec.path, { query: params, signal }),
    placeholderData: keepPreviousData,
  });
  // reference pickers too: a converted lead adds a client, a new lead / contact is pickable at once
  const refresh = () => Promise.all([client.invalidateQueries({ queryKey: ["records", spec.path] }), client.invalidateQueries({ queryKey: ["records", "ref"] })]);
  const fields = usable(spec.fields, refs);
  const defaults = React.useMemo(() => {
    const d: Record<string, string> = {};
    for (const f of fields) if (f.type === "ref" && f.required && refs[f.ref!]?.length === 1) d[f.name] = refs[f.ref!]![0]!.id; // only choice (me / my department)
    return d;
  }, [fields, refs]);
  const archive = useMutation({
    mutationFn: (row: Row) => apiRequest(`${spec.path}/${row.id}`, { method: "DELETE", idempotent: true }),
    onSuccess: () => { toast.push(t("archived")); setArchiving(null); void refresh(); },
    onError: (e) => toast.push(errorText(tAll, e), "danger"),
  });
  const rows = list.data?.data ?? [];
  const pg = list.data?.meta?.pagination;
  const allowed = (a: ActionSpec) =>
    (a.permission ? caps.permissions.includes(a.permission) : caps.canWrite) && (a.allowed?.({ role: caps.role, scopePillars: caps.scopePillars }) ?? true);
  const label = t(`resource.${spec.key}` as "me");
  // detail pages are narrower than the list (REV reads clients here, but not `/business/sales/clients/*`)
  const detailHref = (row: Row) => {
    const href = spec.detailHref?.(row);
    return href && canAccess(href, caps.role, caps.permissions, caps.scopePillars) ? href : null;
  };

  return (
    <section className="flex flex-col gap-3" data-testid={`records-${spec.key}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        {spec.searchable
          ? <Input className="max-w-xs" placeholder={t("search")} aria-label={t("search")} value={q} onChange={(e) => { setQ(e.target.value); setOffset(0); }} data-testid={`records-${spec.key}-search`} />
          : <span />}
        {caps.canWrite && <Button size="sm" onClick={() => setEditing("new")} data-testid={`records-${spec.key}-create`}>{t("create", { resource: label })}</Button>}
      </div>
      {list.isPending && <div className="h-32 animate-pulse rounded-lg bg-muted" />}
      {list.isError && <QueryError error={list.error} onRetry={() => void list.refetch()} testId={`records-${spec.key}-error`} />}
      {list.isSuccess && rows.length === 0 && <p className="text-sm text-muted-foreground" data-testid={`records-${spec.key}-empty`}>{t("empty")}</p>}
      {rows.length > 0 && (
        <Card className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-sm" data-testid={`records-${spec.key}-table`}>
            <thead className="border-b bg-muted/50 text-left text-xs text-muted-foreground">
              <tr>
                {spec.columns.map((c) => spec.sortable?.includes(c.name)
                  ? <SortHeader key={c.name} field={c.name} label={t(`field.${c.name}` as "me")} sort={sort} onSort={onSort} />
                  : <th key={c.name} scope="col" className="px-3 py-2 font-medium">{t(`field.${c.name}` as "me")}</th>)}
                <th scope="col" className="px-3 py-2"><span className="sr-only">{t("actions")}</span></th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {rows.map((row) => (
                <tr key={row.id} data-testid="record-row" data-id={row.id}>
                  {spec.columns.map((c, i) => {
                    const href = i === 0 ? detailHref(row) : null;
                    return (
                      <td key={c.name} className="px-3 py-2">
                        {href
                          ? <Link href={href} className="font-medium text-primary hover:underline" data-testid="record-open"><Cell col={c} row={row} refs={refs} /></Link>
                          : <Cell col={c} row={row} refs={refs} />}
                      </td>
                    );
                  })}
                  <td className="whitespace-nowrap px-3 py-2 text-right">
                    {(spec.actions ?? []).filter((a) => allowed(a) && a.visible(row)).map((a) => (
                      <Button key={a.key} size="sm" variant="outline" className="mr-1" onClick={() => setActing({ action: a, row })} data-testid={`record-action-${a.key}`}>{t(`action.${spec.key}.${a.key}` as "me")}</Button>
                    ))}
                    {caps.canWrite && (spec.editable?.(row) ?? true) && <Button size="sm" variant="ghost" onClick={() => setEditing(row)} data-testid="record-edit">{t("edit")}</Button>}
                    {caps.canWrite && spec.archivable && (spec.editable?.(row) ?? true) && <Button size="sm" variant="ghost" className="text-danger" onClick={() => setArchiving(row)} data-testid="record-archive">{t("archive")}</Button>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
      {pg && pg.total > PAGE && (
        <div className="flex items-center justify-end gap-2 text-sm">
          <span className="text-muted-foreground">{t("page", { from: offset + 1, to: Math.min(offset + PAGE, pg.total), total: pg.total })}</span>
          <Button size="sm" variant="outline" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE))}>{t("prev")}</Button>
          <Button size="sm" variant="outline" disabled={!pg.has_next} onClick={() => setOffset(offset + PAGE)}>{t("next")}</Button>
        </div>
      )}

      <FormDialog
        open={editing !== null}
        onClose={() => setEditing(null)}
        title={t(editing === "new" ? "create" : "editTitle", { resource: label })}
        testId={`records-${spec.key}-editor`}
        fields={fields}
        row={editing && editing !== "new" ? editing : undefined}
        defaults={defaults}
        refs={refs}
        submit={async (v, extra) => {
          if (editing === "new") await apiRequest(spec.path, { method: "POST", body: { ...createBody(fields, v), ...extra }, idempotent: true });
          else if (editing) await apiRequest(`${spec.path}/${editing.id}`, { method: "PATCH", body: updateBody(fields, v, editing), idempotent: true });
          toast.push(t(editing === "new" ? "created" : "updated"));
          void refresh();
        }}
      />
      {acting && (
        <FormDialog
          open
          onClose={() => setActing(null)}
          title={t(`action.${spec.key}.${acting.action.key}` as "me")}
          testId={`records-${spec.key}-action`}
          fields={acting.action.fields}
          refs={refs}
          submit={async (v) => {
            await apiRequest(`${spec.path}/${acting.row.id}/${acting.action.suffix}`, { method: "POST", body: createBody(acting.action.fields, v), idempotent: true });
            toast.push(t("done"));
            void refresh();
          }}
        />
      )}
      <Dialog open={archiving !== null} onOpenChange={(o) => !o && setArchiving(null)}>
        <DialogContent data-testid={`records-${spec.key}-archive-dialog`}>
          <DialogTitle>{t("archiveTitle", { resource: label })}</DialogTitle>
          <DialogDescription>{t("archiveConfirm")}</DialogDescription>
          <div className="mt-4 flex justify-end gap-2">
            <DialogClose asChild><Button type="button" variant="ghost">{t("cancel")}</Button></DialogClose>
            <Button type="button" variant="danger" disabled={archive.isPending} onClick={() => archiving && archive.mutate(archiving)} data-testid="record-archive-confirm">{t("archive")}</Button>
          </div>
        </DialogContent>
      </Dialog>
    </section>
  );
}

/** "Add" button + create dialog for one resource with preset values (CRM detail views, R-DEC-176). */
export function QuickCreate({ resource, caps, defaults, onCreated, testId }: {
  resource: string; caps: RecordCaps; defaults: Record<string, string>; onCreated?: () => void; testId: string;
}) {
  const t = useTranslations("records");
  const toast = useToast();
  const client = useQueryClient();
  const spec = RESOURCES.find((r) => r.key === resource)!;
  const refs = useRefs(caps, (k) => t(k as "me"), React.useMemo(() => refKindsOf(spec), [spec]));
  const [open, setOpen] = React.useState(false);
  if (!caps.canWrite) return null;
  const fields = usable(spec.fields, refs);
  const title = t("create", { resource: t(`resource.${spec.key}` as "me") });
  return (
    <>
      <Button size="sm" variant="outline" onClick={() => setOpen(true)} data-testid={testId}>{title}</Button>
      <FormDialog
        open={open}
        onClose={() => setOpen(false)}
        title={title}
        testId={`${testId}-editor`}
        fields={fields}
        defaults={defaults}
        refs={refs}
        submit={async (v, extra) => {
          await apiRequest(spec.path, { method: "POST", body: { ...createBody(fields, v), ...extra }, idempotent: true });
          toast.push(t("created"));
          void client.invalidateQueries({ queryKey: ["records"] });
          onCreated?.();
        }}
      />
    </>
  );
}

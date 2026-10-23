"use client";
/**
 * SCR-53 `/admin/users` (T-617F): EP-ADM-05 table with role / status / department / search
 * filters; create (EP-ADM-06) + edit (EP-ADM-08) forms (rhf + zod, `scope_pillars` only for
 * DIR, initial password with eye toggle); lock / unlock with confirm + reason (EP-ADM-09/10).
 * No self-lock / self role change (disabled + tooltip). CEO = read only.
 */
import * as React from "react";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useLocale, useTranslations } from "next-intl";
import { Eye, EyeOff } from "lucide-react";
import type { Api } from "@aureon/shared-types";
import { apiRequest } from "@/lib/api-client";
import { formatDateTime, type AppLocale } from "@/lib/format";
import { qk } from "@/lib/query-keys";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { AdminHeader, ConfirmDialog, Field, useErrorText } from "./common";
import { useDepartments } from "./org/use-org";

type UserOut = Api.UserAdminOut;
export const GRANTABLE_ROLES = ["CEO", "DIR", "MGR", "EMP", "REV", "ADM"] as const;
export const PILLARS = ["F", "O", "C", "U", "S"] as const;
const PAGE = 20;

export function UsersView({ canEdit, selfId, actorRole }: { canEdit: boolean; selfId: string; actorRole: string }) {
  const t = useTranslations();
  const locale = useLocale() as AppLocale;
  const toast = useToast();
  const qc = useQueryClient();
  const [filters, setFilters] = React.useState({ role_code: "", is_active: "", department_id: "", q: "" });
  const [offset, setOffset] = React.useState(0);
  const [editing, setEditing] = React.useState<UserOut | "new" | null>(null);
  const [locking, setLocking] = React.useState<UserOut | null>(null);
  const params = { ...filters, limit: PAGE, offset };
  const res = useQuery({
    queryKey: qk.users(params),
    queryFn: ({ signal }) => apiRequest<UserOut[]>("/platform/users", { query: { ...params, role_code: params.role_code || undefined, is_active: params.is_active || undefined, department_id: params.department_id || undefined, q: params.q || undefined }, signal }),
    placeholderData: keepPreviousData,
  });
  const depts = useDepartments();
  const deptName = (id: string | null) => depts.data?.data.find((d) => d.id === id)?.code ?? "—";
  const setF = (k: keyof typeof filters, v: string) => { setFilters((f) => ({ ...f, [k]: v })); setOffset(0); };
  const lock = useMutation({
    mutationFn: ({ u, reason }: { u: UserOut; reason: string }) => apiRequest<UserOut>(`/platform/users/${u.id}/${u.is_active ? "deactivate" : "reactivate"}`, { method: "POST", idempotent: true, body: { reason } }),
    onSuccess: (_d, { u }) => {
      void qc.invalidateQueries({ queryKey: ["admin", "users"] });
      toast.push(u.is_active ? t("usersAdmin.lockedToast", { name: u.full_name }) : t("usersAdmin.unlockedToast", { name: u.full_name }));
    },
  });
  const items = res.data?.data ?? [];
  const pg = res.data?.meta?.pagination;
  const canTouch = (u: UserOut) => canEdit && !u.is_service_account && (u.role_code !== "CEO" || actorRole === "CEO");
  return (
    <TooltipProvider>
      <div className="mx-auto flex max-w-[1400px] flex-col gap-4" data-testid="users-admin">
        <AdminHeader title={t("usersAdmin.title")} hint={canEdit ? t("usersAdmin.hint") : t("usersAdmin.readOnly")}>
          {pg && <span className="text-sm text-muted-foreground" data-testid="users-total">{t("usersAdmin.total", { total: pg.total })}</span>}
          {canEdit && <Button size="sm" onClick={() => setEditing("new")} data-testid="user-new">{t("usersAdmin.new")}</Button>}
        </AdminHeader>
        <div className="flex flex-wrap gap-2">
          <Input className="max-w-xs" placeholder={t("usersAdmin.search")} aria-label={t("usersAdmin.search")} value={filters.q} onChange={(e) => setF("q", e.target.value)} data-testid="user-search" />
          <NativeSelect aria-label={t("usersAdmin.col.role")} value={filters.role_code} onChange={(e) => setF("role_code", e.target.value)} data-testid="user-filter-role">
            <option value="">{t("usersAdmin.allRoles")}</option>
            {[...GRANTABLE_ROLES, "AI"].map((r) => <option key={r} value={r}>{t(`role.${r}` as "role.CEO")}</option>)}
          </NativeSelect>
          <NativeSelect aria-label={t("usersAdmin.col.status")} value={filters.is_active} onChange={(e) => setF("is_active", e.target.value)} data-testid="user-filter-status">
            <option value="">{t("usersAdmin.allStatus")}</option>
            <option value="true">{t("usersAdmin.active")}</option>
            <option value="false">{t("usersAdmin.locked")}</option>
          </NativeSelect>
          <NativeSelect aria-label={t("usersAdmin.col.department")} value={filters.department_id} onChange={(e) => setF("department_id", e.target.value)} data-testid="user-filter-dept">
            <option value="">{t("positionsAdmin.allDepts")}</option>
            {(depts.data?.data ?? []).map((d) => <option key={d.id} value={d.id}>{d.code} — {d.name}</option>)}
          </NativeSelect>
        </div>
        {res.isPending && <div className="h-40 animate-pulse rounded-lg bg-muted" />}
        {res.isError && <p role="alert" className="text-danger">{t("errors.generic")}</p>}
        {res.isSuccess && !items.length && <p className="text-muted-foreground">{t("usersAdmin.empty")}</p>}
        {items.length > 0 && (
          <Card className="overflow-x-auto">
            <table className="w-full min-w-[900px] text-sm" data-testid="users-table">
              <thead className="border-b bg-muted/50 text-left text-xs text-muted-foreground">
                <tr>{(["name", "role", "department", "status", "lastLogin"] as const).map((c) => <th key={c} scope="col" className="px-3 py-2 font-medium">{t(`usersAdmin.col.${c}`)}</th>)}<th className="px-3 py-2"><span className="sr-only">{t("usersAdmin.actions")}</span></th></tr>
              </thead>
              <tbody className="divide-y">
                {items.map((u) => {
                  const self = u.id === selfId;
                  return (
                    <tr key={u.id} data-testid="user-row" data-email={u.email} data-active={u.is_active}>
                      <td className="px-3 py-2"><div className="font-medium">{u.full_name}</div><div className="text-xs text-muted-foreground">{u.email}</div></td>
                      <td className="px-3 py-2">{t(`role.${u.role_code}` as "role.CEO")}{u.scope_pillars.length > 0 && <span className="ml-1 text-xs text-muted-foreground">({u.scope_pillars.join(", ")})</span>}</td>
                      <td className="px-3 py-2">{deptName(u.department_id)}</td>
                      <td className="px-3 py-2"><Badge variant={u.is_active ? "success" : "danger"} data-testid="user-status">{t(u.is_active ? "usersAdmin.active" : "usersAdmin.locked")}</Badge></td>
                      <td className="px-3 py-2 tabular-nums">{u.last_login_at ? formatDateTime(u.last_login_at, locale) : "—"}</td>
                      <td className="px-3 py-2 text-right">
                        {canTouch(u) && (
                          <div className="flex justify-end gap-1">
                            <Button size="sm" variant="ghost" onClick={() => setEditing(u)} data-testid="user-edit">{t("orgAdmin.edit")}</Button>
                            <Guard disabled={self} reason={t("usersAdmin.selfLock")}>
                              <Button size="sm" variant={u.is_active ? "outline" : "success"} disabled={self} onClick={() => setLocking(u)} data-testid="user-lock">{t(u.is_active ? "usersAdmin.lock" : "usersAdmin.unlock")}</Button>
                            </Guard>
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </Card>
        )}
        {pg && pg.total > PAGE && (
          <div className="flex items-center justify-end gap-3 text-sm">
            <span className="tabular-nums text-muted-foreground">{t("idp.pageInfo", { from: offset + 1, to: Math.min(offset + PAGE, pg.total), total: pg.total })}</span>
            <Button size="sm" variant="outline" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE))}>{t("buttons.previous")}</Button>
            <Button size="sm" variant="outline" disabled={!pg.has_next} onClick={() => setOffset(offset + PAGE)}>{t("buttons.next")}</Button>
          </div>
        )}
        {canEdit && <UserDialog editing={editing} onClose={() => setEditing(null)} selfId={selfId} actorRole={actorRole} departments={depts.data?.data ?? []} />}
        <ConfirmDialog open={locking !== null} onOpenChange={(o) => !o && setLocking(null)} testId="user-lock-dialog" reasonRequired danger={locking?.is_active}
          title={t(locking?.is_active ? "usersAdmin.lockTitle" : "usersAdmin.unlockTitle", { name: locking?.full_name ?? "" })}
          body={locking?.is_active ? t("usersAdmin.lockBody") : undefined} confirmLabel={t(locking?.is_active ? "usersAdmin.lock" : "usersAdmin.unlock")}
          onConfirm={async (reason) => { if (locking) await lock.mutateAsync({ u: locking, reason }); }} />
      </div>
    </TooltipProvider>
  );
}

/** Disabled control + tooltip explaining why (§8.2: a disabled button does not get focus → wrap it). */
function Guard({ disabled, reason, children }: { disabled: boolean; reason: string; children: React.ReactNode }) {
  if (!disabled) return <>{children}</>;
  return (
    <Tooltip>
      <TooltipTrigger asChild><span tabIndex={0} aria-label={reason}>{children}</span></TooltipTrigger>
      <TooltipContent>{reason}</TooltipContent>
    </Tooltip>
  );
}

function UserDialog({ editing, onClose, selfId, actorRole, departments }: { editing: UserOut | "new" | null; onClose: () => void; selfId: string; actorRole: string; departments: { id: string; code: string; name: string }[] }) {
  const t = useTranslations();
  const toast = useToast();
  const errText = useErrorText();
  const qc = useQueryClient();
  const current = editing && editing !== "new" ? editing : null;
  const self = current?.id === selfId;
  const roles = GRANTABLE_ROLES.filter((r) => r !== "CEO" || actorRole === "CEO");
  const [show, setShow] = React.useState(false);
  const schema = React.useMemo(() => z.object({
    email: z.string().trim().email(t("auth.emailInvalid")),
    full_name: z.string().trim().min(1, t("orgAdmin.form.required")).max(200),
    role_code: z.enum(GRANTABLE_ROLES),
    scope_pillars: z.array(z.enum(PILLARS)),
    department_id: z.string(),
    locale: z.enum(["vi", "en"]),
    initial_password: z.string(),
  }).superRefine((v, ctx) => {
    if (!current && v.initial_password.length < 12) ctx.addIssue({ code: "custom", path: ["initial_password"], message: t("usersAdmin.passwordMin") });
    if (v.role_code === "DIR" && v.scope_pillars.length === 0) ctx.addIssue({ code: "custom", path: ["scope_pillars"], message: t("usersAdmin.pillarsRequired") });
  }), [t, current]);
  type V = z.infer<typeof schema>;
  const form = useForm<V>({ resolver: zodResolver(schema) });
  React.useEffect(() => {
    if (editing) {
      setShow(false);
      form.reset({ email: current?.email ?? "", full_name: current?.full_name ?? "", role_code: (current?.role_code as V["role_code"] | undefined) ?? "EMP",
        scope_pillars: (current?.scope_pillars ?? []) as V["scope_pillars"], department_id: current?.department_id ?? "", locale: current?.locale === "en" ? "en" : "vi", initial_password: "" });
    }
  }, [editing, current, form]);
  const role = form.watch("role_code");
  const save = useMutation({
    mutationFn: (v: V) => {
      const pillars = v.role_code === "DIR" ? v.scope_pillars : [];
      return current
        ? apiRequest<UserOut>(`/platform/users/${current.id}`, { method: "PATCH", body: { full_name: v.full_name, ...(self ? {} : { role_code: v.role_code, scope_pillars: pillars }), department_id: v.department_id || null, locale: v.locale, version: current.version } })
        : apiRequest<UserOut>("/platform/users", { method: "POST", idempotent: true, body: { email: v.email, full_name: v.full_name, role_code: v.role_code, scope_pillars: pillars, department_id: v.department_id || null, locale: v.locale, initial_password: v.initial_password } });
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "users"] }),
  });
  const submit = form.handleSubmit(async (v) => {
    await save.mutateAsync(v);
    toast.push(t(current ? "usersAdmin.updatedToast" : "usersAdmin.createdToast", { name: v.full_name }));
    onClose();
  });
  const e = form.formState.errors;
  return (
    <Dialog open={editing !== null} onOpenChange={(o) => { if (!o) { save.reset(); onClose(); } }}>
      <DialogContent data-testid="user-form">
        <DialogTitle>{t(current ? "usersAdmin.edit" : "usersAdmin.new")}</DialogTitle>
        <DialogDescription className="sr-only">{t("usersAdmin.hint")}</DialogDescription>
        <form onSubmit={(ev) => void submit(ev)} className="mt-4 flex flex-col gap-3" noValidate>
          <Field id="u-email" label={t("auth.email")} error={e.email?.message}><Input id="u-email" type="email" autoComplete="off" disabled={Boolean(current)} {...form.register("email")} aria-invalid={Boolean(e.email)} data-testid="user-email" /></Field>
          <Field id="u-name" label={t("usersAdmin.col.name")} error={e.full_name?.message}><Input id="u-name" {...form.register("full_name")} aria-invalid={Boolean(e.full_name)} data-testid="user-name" /></Field>
          <div className="grid grid-cols-2 gap-3">
            <Field id="u-role" label={t("usersAdmin.col.role")}>
              <NativeSelect id="u-role" {...form.register("role_code")} disabled={self} title={self ? t("usersAdmin.selfRole") : undefined} data-testid="user-role">
                {roles.map((r) => <option key={r} value={r}>{t(`role.${r}` as "role.CEO")}</option>)}
              </NativeSelect>
              {self && <p className="text-xs text-muted-foreground">{t("usersAdmin.selfRole")}</p>}
            </Field>
            <Field id="u-locale" label={t("header.language")}>
              <NativeSelect id="u-locale" {...form.register("locale")} data-testid="user-locale"><option value="vi">{t("header.vi")}</option><option value="en">{t("header.en")}</option></NativeSelect>
            </Field>
          </div>
          {role === "DIR" && (
            <fieldset className="flex flex-col gap-1.5" data-testid="user-pillars">
              <legend className="text-sm font-medium">{t("usersAdmin.pillars")}</legend>
              <div className="flex flex-wrap gap-3">
                {PILLARS.map((p) => (
                  <label key={p} className="flex items-center gap-1.5 text-sm">
                    <input type="checkbox" value={p} {...form.register("scope_pillars")} disabled={self} data-testid={`user-pillar-${p}`} /> {t(`usersAdmin.pillar.${p}`)}
                  </label>
                ))}
              </div>
              {e.scope_pillars && <p className="text-xs text-danger">{e.scope_pillars.message}</p>}
            </fieldset>
          )}
          <Field id="u-dept" label={t("usersAdmin.col.department")}>
            <NativeSelect id="u-dept" {...form.register("department_id")} data-testid="user-dept">
              <option value="">{t("common.none")}</option>
              {departments.map((d) => <option key={d.id} value={d.id}>{d.code} — {d.name}</option>)}
            </NativeSelect>
          </Field>
          {!current && (
            <Field id="u-pass" label={t("usersAdmin.initialPassword")} error={e.initial_password?.message}>
              <div className="relative">
                <Input id="u-pass" type={show ? "text" : "password"} autoComplete="new-password" className="pr-10" {...form.register("initial_password")} aria-invalid={Boolean(e.initial_password)} data-testid="user-password" />
                <button type="button" onClick={() => setShow(!show)} className="absolute inset-y-0 right-0 flex w-10 items-center justify-center text-muted-foreground" aria-label={t(show ? "auth.hidePassword" : "auth.showPassword")} aria-pressed={show} data-testid="user-password-toggle">
                  {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </Field>
          )}
          {save.isError && <p role="alert" className="text-sm text-danger" data-testid="user-form-error">{errText(save.error)}</p>}
          <div className="mt-2 flex justify-end gap-2">
            <DialogClose asChild><Button type="button" variant="ghost">{t("buttons.cancel")}</Button></DialogClose>
            <Button type="submit" disabled={save.isPending} data-testid="user-form-submit">{t("buttons.save")}</Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

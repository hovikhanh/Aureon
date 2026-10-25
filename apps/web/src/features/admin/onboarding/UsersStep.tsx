"use client";
import * as React from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { KeyRound } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";
import { apiRequest, newIdempotencyKey } from "@/lib/api-client";
import { useErrorText } from "@/features/admin/common";
import { todayIso, useOrgTree } from "@/features/admin/org/use-org";
import { MAX_USER_ROWS, MIN_PASSWORD, randomPassword, suggestRole, type MemberLite } from "./logic";
import type { StepProps } from "./OnboardingWizard";
import { useAllUsers } from "./use-onboarding";

type Role = "CEO" | "DIR" | "MGR" | "EMP" | "REV" | "ADM";
interface Row extends MemberLite { pick: boolean; email: string; password: string; role: Role; result: "idle" | "ok" | "error"; error?: string }
const EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

/**
 * Step 4 — users + roles from `members[]` of EP-ORG-24 (ADM never reads employee records — R-DEC-30). Each
 * picked row: e-mail + initial password (≥ 12, generator shown once) → EP-ADM-06 one by one, one
 * Idempotency-Key per row, ≤ 30 rows per run, a failed row never blocks the others. ADM cannot grant CEO
 * (R-DEC-36). `complete_step users` after ≥ 1 new user or "Enough".
 */
export function UsersStep({ state, viewer, patch, goTo }: StepProps) {
  const t = useTranslations();
  const tree = useOrgTree(todayIso());
  const users = useAllUsers();
  if (tree.isPending || users.isPending) return <div className="h-48 animate-pulse rounded bg-muted" />;
  if (tree.isError || users.isError) return <p role="alert" className="text-danger">{t("errors.generic")}</p>;
  const linked = new Set(users.data.map((u) => u.employee_id).filter(Boolean));
  const members: MemberLite[] = tree.data.data.departments.flatMap((d) => d.members.filter((m) => !linked.has(m.employee_id))
    .map((m) => ({ employee_id: m.employee_id, employee_code: m.employee_code, full_name: m.full_name, department_id: d.id, is_head: d.manager_id === m.employee_id })));
  const hasCeo = users.data.some((u) => u.role_code === "CEO" && u.is_active);
  return <UsersTable members={members} hasCeo={hasCeo} state={state} viewer={viewer} patch={patch} goTo={goTo} />;
}

function UsersTable({ members, hasCeo, state, viewer, patch, goTo }: StepProps & { members: MemberLite[]; hasCeo: boolean }) {
  const t = useTranslations();
  const toast = useToast();
  const errText = useErrorText();
  const client = useQueryClient();
  const [rows, setRows] = React.useState<Row[]>(() => members.map((m) => ({ ...m, pick: false, email: "", password: "", role: suggestRole(m), result: "idle" })));
  const [created, setCreated] = React.useState(0);
  const [busy, setBusy] = React.useState(false);
  const set = (id: string, p: Partial<Row>) => setRows((xs) => xs.map((r) => (r.employee_id === id ? { ...r, ...p } : r)));
  const picked = rows.filter((r) => r.pick && r.result !== "ok");
  const roles: Role[] = viewer.role === "CEO" ? ["CEO", "DIR", "MGR", "EMP", "REV", "ADM"] : ["DIR", "MGR", "EMP", "REV", "ADM"];
  const rowError = (r: Row): string | null => (!EMAIL.test(r.email) ? t("onboarding.users.emailInvalid") : r.password.length < MIN_PASSWORD ? t("usersAdmin.passwordMin") : null);

  const run = async () => {
    setBusy(true);
    let ok = 0;
    for (const r of picked.slice(0, MAX_USER_ROWS)) {
      const bad = rowError(r);
      if (bad) { set(r.employee_id, { result: "error", error: bad }); continue; }
      try {
        await apiRequest("/platform/users", { method: "POST", headers: { "idempotency-key": newIdempotencyKey() },
          body: { email: r.email.trim(), full_name: r.full_name, role_code: r.role, department_id: r.department_id, employee_id: r.employee_id, initial_password: r.password } });
        set(r.employee_id, { result: "ok", error: undefined, password: "" });
        ok += 1;
      } catch (e) {
        set(r.employee_id, { result: "error", error: errText(e) });
      }
    }
    setCreated((n) => n + ok);
    if (ok) { toast.push(t("onboarding.users.created", { n: ok })); void client.invalidateQueries({ queryKey: ["admin", "users"] }); }
    setBusy(false);
  };
  const finish = async () => {
    setBusy(true);
    try { await patch(state, "complete_step", "users", { users_created: created }); goTo("goals_import"); } catch (e) { toast.push(errText(e), "danger"); } finally { setBusy(false); }
  };

  return (
    <div className="flex flex-col gap-3" data-testid="users-step">
      <p className="text-sm text-muted-foreground">{t("onboarding.users.hint", { max: MAX_USER_ROWS })}</p>
      {!hasCeo && <p role="status" className="rounded border border-warning bg-warning-subtle p-2 text-sm" data-testid="users-no-ceo">{t("onboarding.users.needCeo")}</p>}
      <div className="max-h-[28rem] overflow-auto">
        <table className="w-full text-sm" data-testid="users-table">
          <thead><tr className="border-b text-left text-muted-foreground">
            <th className="py-2 pr-2 font-medium"><span className="sr-only">{t("onboarding.users.pick")}</span></th>
            <th className="pr-2 font-medium">{t("onboarding.users.employee")}</th><th className="pr-2 font-medium">{t("onboarding.users.role")}</th>
            <th className="pr-2 font-medium">Email</th><th className="pr-2 font-medium">{t("usersAdmin.initialPassword")}</th><th className="font-medium">{t("onboarding.users.result")}</th>
          </tr></thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.employee_id} className="border-b align-top last:border-0" data-testid="user-row" data-code={r.employee_code} data-result={r.result}>
                <td className="py-1.5 pr-2"><input type="checkbox" checked={r.pick} disabled={r.result === "ok" || busy} onChange={(e) => set(r.employee_id, { pick: e.target.checked })} aria-label={t("onboarding.users.pickRow", { name: r.full_name })} data-testid="user-pick" /></td>
                <td className="pr-2">{r.employee_code} — {r.full_name}{r.is_head && <span className="ml-1 text-xs text-muted-foreground">({t("onboarding.users.head")})</span>}</td>
                <td className="pr-2"><NativeSelect value={r.role} onChange={(e) => set(r.employee_id, { role: e.target.value as Role })} disabled={r.result === "ok"} className="w-28" aria-label={t("onboarding.users.role")} data-testid="user-role">
                  {roles.map((x) => <option key={x} value={x}>{t(`role.${x}` as "role.CEO")}</option>)}</NativeSelect></td>
                <td className="pr-2"><Input value={r.email} onChange={(e) => set(r.employee_id, { email: e.target.value, pick: true })} disabled={r.result === "ok"} className="w-52" aria-label={t("onboarding.users.emailOf", { name: r.full_name })} data-testid="user-email" /></td>
                <td className="pr-2"><div className="flex gap-1">
                  <Input value={r.password} onChange={(e) => set(r.employee_id, { password: e.target.value })} disabled={r.result === "ok"} className="w-44 font-mono" aria-label={t("onboarding.users.passwordOf", { name: r.full_name })} data-testid="user-password" autoComplete="new-password" />
                  <Button type="button" size="sm" variant="ghost" onClick={() => set(r.employee_id, { password: randomPassword() })} disabled={r.result === "ok"} aria-label={t("onboarding.users.generate")} data-testid="user-generate"><KeyRound className="h-4 w-4" aria-hidden /></Button>
                </div></td>
                <td className="text-xs">{r.result === "ok" ? <span className="text-success">{t("onboarding.users.ok")}</span> : r.error ? <span role="alert" className="text-danger" data-testid="user-error">{r.error}</span> : null}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length === 0 && <p className="py-4 text-sm text-muted-foreground" data-testid="users-empty">{t("onboarding.users.empty")}</p>}
      </div>
      <div className="flex flex-wrap items-center justify-end gap-2">
        {picked.length > MAX_USER_ROWS && <span className="text-sm text-warning">{t("onboarding.users.tooMany", { max: MAX_USER_ROWS })}</span>}
        <Button variant="outline" onClick={() => void run()} disabled={busy || picked.length === 0} data-testid="users-create">{t("onboarding.users.create", { n: Math.min(picked.length, MAX_USER_ROWS) })}</Button>
        <Button onClick={() => void finish()} disabled={busy} data-testid="users-enough">{created ? t("onboarding.saveContinue") : t("onboarding.users.enough")}</Button>
      </div>
    </div>
  );
}

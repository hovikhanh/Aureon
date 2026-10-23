"use client";
/** SCR-54 `/admin/roles` (T-617F): EP-ADM-11 matrix 7 roles × `<domain>:<action>` (✓/—) + scope notes; read only at P0. */
import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import type { Api } from "@aureon/shared-types";
import { apiRequest } from "@/lib/api-client";
import { qk } from "@/lib/query-keys";
import { Card } from "@/components/ui/card";
import { AdminHeader } from "./common";

export const ROLE_ORDER = ["CEO", "DIR", "MGR", "EMP", "REV", "ADM", "AI"];

/** Rows = every permission any role holds, grouped by domain in a stable order. */
export function permissionRows(roles: readonly { permissions: string[] }[]): string[] {
  const actions = ["read", "write", "query", "approve", "admin"];
  return [...new Set(roles.flatMap((r) => r.permissions))].sort((a, b) => {
    const [da = "", aa = ""] = a.split(":");
    const [db = "", ab = ""] = b.split(":");
    return da === db ? actions.indexOf(aa) - actions.indexOf(ab) : da.localeCompare(db);
  });
}

export function RolesView() {
  const t = useTranslations();
  const locale = useLocale();
  const res = useQuery({ queryKey: qk.roles(), queryFn: ({ signal }) => apiRequest<Api.RoleOut[]>("/platform/roles", { signal }) });
  const roles = [...(res.data?.data ?? [])].sort((a, b) => ROLE_ORDER.indexOf(a.code) - ROLE_ORDER.indexOf(b.code));
  const rows = permissionRows(roles);
  return (
    <div className="mx-auto flex max-w-[1400px] flex-col gap-4" data-testid="roles-admin">
      <AdminHeader title={t("rolesAdmin.title")} hint={t("rolesAdmin.hint")} />
      {res.isPending && <div className="h-64 animate-pulse rounded-lg bg-muted" />}
      {res.isError && <p role="alert" className="text-danger">{t("errors.generic")}</p>}
      {roles.length > 0 && (
        <Card className="overflow-x-auto">
          <table className="w-full min-w-[900px] text-sm" data-testid="roles-matrix">
            <caption className="sr-only">{t("rolesAdmin.caption")}</caption>
            <thead className="border-b bg-muted/50 text-xs text-muted-foreground">
              <tr>
                <th scope="col" className="px-3 py-2 text-left font-medium">{t("rolesAdmin.permission")}</th>
                {roles.map((r) => (
                  <th key={r.code} scope="col" className="px-3 py-2 text-center font-medium" data-testid="role-col" data-code={r.code}>
                    <div>{r.code}</div><div className="font-normal">{locale === "en" ? r.name_en : r.name_vi}</div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {rows.map((p) => (
                <tr key={p} data-testid="perm-row" data-perm={p}>
                  <th scope="row" className="px-3 py-1.5 text-left font-mono text-xs font-normal">{p}</th>
                  {roles.map((r) => {
                    const has = r.permissions.includes(p);
                    const scope = (r.scope_rules as Record<string, string>)[p];
                    return (
                      <td key={r.code} className="px-3 py-1.5 text-center" data-testid="perm-cell" data-has={has}>
                        {has ? <span className="text-success" aria-label={t("rolesAdmin.granted")}>✓{scope && <sup className="ml-0.5 text-[10px] text-muted-foreground">{scope}</sup>}</span> : <span className="text-muted-foreground" aria-label={t("rolesAdmin.notGranted")}>—</span>}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
      <Card className="p-4 text-sm" data-testid="roles-legend">
        <h2 className="font-semibold">{t("rolesAdmin.legendTitle")}</h2>
        <ul className="mt-2 grid gap-1 sm:grid-cols-2">
          {(["d", "o", "p", "r", "s", "agg"] as const).map((k) => <li key={k}><span className="font-mono">{k}</span> — {t(`rolesAdmin.scope.${k}`)}</li>)}
        </ul>
        <p className="mt-2 text-muted-foreground">{t("rolesAdmin.otherMarks")}</p>
        <p className="mt-3 text-muted-foreground">{t("rolesAdmin.readOnly")}</p>
      </Card>
    </div>
  );
}

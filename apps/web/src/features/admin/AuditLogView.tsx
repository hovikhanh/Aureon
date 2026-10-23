"use client";
import * as React from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/select";
import { apiRequest } from "@/lib/api-client";
import { formatDateTime, type AppLocale } from "@/lib/format";
import { qk } from "@/lib/query-keys";

interface AuditLogOut {
  id: string;
  occurred_at: string;
  actor_type: string;
  actor_role: string | null;
  action: string;
  target_table: string | null;
  target_id: string | null;
}

const PAGE = 20;

/** Local date (YYYY-MM-DD, Asia/Ho_Chi_Minh) → ISO UTC bound for EP-ADM-12 `from` / `to`. */
export function dayBound(day: string, end: boolean): string | undefined {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(day)) return undefined;
  return new Date(`${day}T${end ? "23:59:59.999" : "00:00:00.000"}+07:00`).toISOString();
}

/** SCR-14 — EP-52 append-only audit log for ADMIN (T-516) + M1.2 filters `from`/`to`/`actor_type` (EP-ADM-12, T-617F). Read only. */
export function AuditLogView() {
  const t = useTranslations();
  const locale = useLocale() as AppLocale;
  const [action, setAction] = React.useState("");
  const [offset, setOffset] = React.useState(0);
  const [actorType, setActorType] = React.useState("");
  const [from, setFrom] = React.useState("");
  const [to, setTo] = React.useState("");
  const badRange = Boolean(from && to && from > to);
  const params = { action: action || undefined, actor_type: actorType || undefined, from: dayBound(from, false), to: dayBound(to, true), limit: PAGE, offset };
  const res = useQuery({
    queryKey: qk.auditLogs(params),
    queryFn: ({ signal }) => apiRequest<AuditLogOut[]>("/platform/audit-logs", { query: params, signal }),
    placeholderData: keepPreviousData,
    enabled: !badRange,
  });
  const items = res.data?.data ?? [];
  const pg = res.data?.meta?.pagination;
  return (
    <div className="mx-auto flex max-w-[1400px] flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">{t("audit.title")}</h1>
        {pg && <span className="text-sm text-muted-foreground" data-testid="audit-total">{t("audit.total", { total: pg.total })}</span>}
      </div>
      <p className="text-sm text-muted-foreground">{t("audit.appendOnly")}</p>
      <div className="flex flex-wrap items-end gap-2">
        <Input className="max-w-sm" placeholder={t("audit.filterAction")} aria-label={t("audit.filterAction")} value={action} onChange={(e) => { setAction(e.target.value.trim()); setOffset(0); }} data-testid="audit-action" />
        <NativeSelect aria-label={t("audit.actorType")} value={actorType} onChange={(e) => { setActorType(e.target.value); setOffset(0); }} data-testid="audit-actor-type">
          <option value="">{t("audit.allActors")}</option>
          {(["USER", "AI", "SYSTEM"] as const).map((a) => <option key={a} value={a}>{t(`audit.actor.${a}`)}</option>)}
        </NativeSelect>
        <label className="flex flex-col gap-1 text-xs text-muted-foreground">{t("audit.from")}<Input type="date" className="w-40" value={from} onChange={(e) => { setFrom(e.target.value); setOffset(0); }} data-testid="audit-from" /></label>
        <label className="flex flex-col gap-1 text-xs text-muted-foreground">{t("audit.to")}<Input type="date" className="w-40" value={to} onChange={(e) => { setTo(e.target.value); setOffset(0); }} data-testid="audit-to" /></label>
        {(action || actorType || from || to) && <Button size="sm" variant="ghost" onClick={() => { setAction(""); setActorType(""); setFrom(""); setTo(""); setOffset(0); }} data-testid="audit-clear">{t("buttons.clearFilters")}</Button>}
      </div>
      {badRange && <p role="alert" className="text-sm text-danger" data-testid="audit-range-error">{t("audit.badRange")}</p>}
      {res.isPending && <div className="h-40 animate-pulse rounded-lg bg-muted" />}
      {res.isError && <p role="alert" className="text-danger">{t("errors.generic")}</p>}
      {res.isSuccess && !items.length && <p className="text-muted-foreground">{t("audit.empty")}</p>}
      {items.length > 0 && (
        <Card className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-sm" data-testid="audit-table">
            <thead className="border-b bg-muted/50 text-left text-xs text-muted-foreground">
              <tr>{(["time", "actor", "action", "target"] as const).map((c) => <th key={c} scope="col" className="px-3 py-2 font-medium">{t(`audit.col.${c}`)}</th>)}</tr>
            </thead>
            <tbody className="divide-y">
              {items.map((a) => (
                <tr key={a.id} data-testid="audit-row" data-action={a.action}>
                  <td className="px-3 py-2 tabular-nums">{formatDateTime(a.occurred_at, locale)}</td>
                  <td className="px-3 py-2">{a.actor_role ?? a.actor_type}</td>
                  <td className="px-3 py-2 font-mono">{a.action}</td>
                  <td className="px-3 py-2 font-mono text-xs">{a.target_table ?? "—"}{a.target_id ? ` · ${a.target_id.slice(0, 8)}` : ""}</td>
                </tr>
              ))}
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
    </div>
  );
}

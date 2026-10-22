"use client";
import * as React from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { apiRequest } from "@/lib/api-client";
import { formatDate, type AppLocale } from "@/lib/format";
import { qk } from "@/lib/query-keys";

interface EmployeeOut {
  id: string;
  employee_code: string;
  full_name: string;
  title: string | null;
  status: string;
  hire_date: string;
}

const PAGE = 20;

/** Minimal EP-82 employee list (T-516 HR flow; full SCR-O drill-down = S5b-full). */
export function EmployeesView() {
  const t = useTranslations();
  const locale = useLocale() as AppLocale;
  const [q, setQ] = React.useState("");
  const [offset, setOffset] = React.useState(0);
  const params = { q, limit: PAGE, offset, sort_by: "full_name", order: "asc" };
  const res = useQuery({
    queryKey: qk.employees(params),
    queryFn: ({ signal }) => apiRequest<EmployeeOut[]>("/hr/employees", { query: params, signal }),
    placeholderData: keepPreviousData,
  });
  const items = res.data?.data ?? [];
  const pg = res.data?.meta?.pagination;
  return (
    <div className="mx-auto flex max-w-[1400px] flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">{t("hr.employeesTitle")}</h1>
        {pg && <span className="text-sm text-muted-foreground" data-testid="employee-total">{t("hr.total", { total: pg.total })}</span>}
      </div>
      <Input className="max-w-sm" placeholder={t("hr.search")} aria-label={t("hr.search")} value={q} onChange={(e) => { setQ(e.target.value); setOffset(0); }} data-testid="employee-search" />
      {res.isPending && <div className="h-40 animate-pulse rounded-lg bg-muted" />}
      {res.isError && <p role="alert" className="text-danger">{t("errors.generic")}</p>}
      {res.isSuccess && !items.length && <p className="text-muted-foreground">{t("hr.empty")}</p>}
      {items.length > 0 && (
        <Card className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-sm" data-testid="employee-table">
            <thead className="border-b bg-muted/50 text-left text-xs text-muted-foreground">
              <tr>{(["code", "name", "title", "status", "hired"] as const).map((c) => <th key={c} scope="col" className="px-3 py-2 font-medium">{t(`hr.col.${c}`)}</th>)}</tr>
            </thead>
            <tbody className="divide-y">
              {items.map((e) => (
                <tr key={e.id} data-testid="employee-row">
                  <td className="px-3 py-2 font-mono">{e.employee_code}</td>
                  <td className="px-3 py-2">{e.full_name}</td>
                  <td className="px-3 py-2">{e.title ?? "—"}</td>
                  <td className="px-3 py-2">{e.status}</td>
                  <td className="px-3 py-2 tabular-nums">{formatDate(e.hire_date, locale)}</td>
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
          <Button size="sm" variant="outline" disabled={!pg.has_next} onClick={() => setOffset(offset + PAGE)} data-testid="employee-next">{t("buttons.next")}</Button>
        </div>
      )}
    </div>
  );
}

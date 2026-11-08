"use client";
import * as React from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { apiRequest } from "@/lib/api-client";
import { formatDate, formatMoney, type AppLocale } from "@/lib/format";
import { codeLabel } from "@/lib/humanize";
import { qk } from "@/lib/query-keys";
import { SortHeader } from "@/components/SortHeader";
import { nextSort, type SortState } from "@/lib/sort";
import { cn } from "@/lib/utils";
import { QueryError } from "@/components/QueryError";

interface InvoiceOut {
  id: string;
  direction: "IN" | "OUT";
  client_name: string | null;
  counterparty_name: string | null;
  series: string | null;
  number: string;
  issued_on: string;
  total_amount: number;
  currency: string;
  status: string;
}

const PAGE = 20;
/** Columns the EP-6x list can sort (`page_params` whitelist). */
const SORT_FIELD: Partial<Record<string, string>> = { issued: "issued_on", total: "total_amount" };

/** Minimal EP-6x invoice list (S5a: verifies the IDP commit; full SCR-0x Finance in S5b). */
export function InvoicesView() {
  const t = useTranslations();
  const locale = useLocale() as AppLocale;
  const [direction, setDirection] = React.useState<"" | "IN" | "OUT">("");
  const [offset, setOffset] = React.useState(0);
  const [sort, setSort] = React.useState<SortState>({ field: "issued_on", order: "desc" });
  const params = { direction, limit: PAGE, offset, sort_by: sort.field, order: sort.order };
  const onSort = (field: string) => { setSort(nextSort(sort, field)); setOffset(0); };
  const q = useQuery({
    queryKey: qk.invoices(params),
    queryFn: ({ signal }) => apiRequest<InvoiceOut[]>("/finance/invoices", { query: params, signal }),
    placeholderData: keepPreviousData,
  });
  const items = q.data?.data ?? [];
  const pg = q.data?.meta?.pagination;
  return (
    <div className="mx-auto flex max-w-[1400px] flex-col gap-4">
      <h1 className="text-2xl font-semibold">{t("finance.invoicesTitle")}</h1>
      <div className="flex gap-2" role="tablist">
        {(["", "IN", "OUT"] as const).map((d) => (
          <Button key={d || "all"} role="tab" aria-selected={direction === d} size="sm" variant={direction === d ? "default" : "outline"} onClick={() => { setDirection(d); setOffset(0); }} data-testid={`dir-${d || "all"}`}>
            {d ? t(`finance.direction.${d}`) : t("idp.filter.all")}
          </Button>
        ))}
      </div>
      {q.isPending && <div className="h-40 animate-pulse rounded-lg bg-muted" />}
      {q.isError && <QueryError error={q.error} onRetry={() => void q.refetch()} testId="invoices-error" />}
      {q.isSuccess && !items.length && <p className="text-muted-foreground">{t("finance.empty")}</p>}
      {items.length > 0 && (
        <Card className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-sm" data-testid="invoice-table">
            <thead className="border-b bg-muted/50 text-left text-xs text-muted-foreground">
              <tr>{(["number", "direction", "counterparty", "issued", "total", "status"] as const).map((c) => {
                const field = SORT_FIELD[c];
                return field
                  ? <SortHeader key={c} field={field} label={t(`finance.col.${c}`)} sort={sort} onSort={onSort} className={cn(c === "total" && "text-right")} />
                  : <th key={c} scope="col" className="px-3 py-2 font-medium">{t(`finance.col.${c}`)}</th>;
              })}</tr>
            </thead>
            <tbody className="divide-y">
              {items.map((i) => (
                <tr key={i.id} data-testid="invoice-row" data-number={i.number}>
                  <td className="px-3 py-2 font-mono">{i.series ? `${i.series}-` : ""}{i.number}</td>
                  <td className="px-3 py-2">{t(`finance.direction.${i.direction}`)}</td>
                  <td className="px-3 py-2">{i.client_name ?? i.counterparty_name ?? "—"}</td>
                  <td className="px-3 py-2 tabular-nums">{formatDate(i.issued_on, locale)}</td>
                  <td className="px-3 py-2 text-right tabular-nums">{formatMoney(i.total_amount, locale)}</td>
                  <td className="px-3 py-2" data-status={i.status}>{codeLabel(t as never, "records.enum.status", i.status)}</td>
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

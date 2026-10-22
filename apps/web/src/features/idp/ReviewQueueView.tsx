"use client";
import * as React from "react";
import Link from "next/link";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { Inbox } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/select";
import { ConfidenceBadge } from "@/components/ConfidenceBadge";
import { apiRequest } from "@/lib/api-client";
import { formatNumber, type AppLocale } from "@/lib/format";
import { qk } from "@/lib/query-keys";
import { DOC_TYPES, QUEUE_STATUSES, type ReviewQueueItem } from "./types";
import { UploadButton } from "./UploadButton";

const PAGE = 20;

export function ReviewQueueView({ userId }: { userId: string }) {
  const t = useTranslations();
  const locale = useLocale() as AppLocale;
  const [status, setStatus] = React.useState("");
  const [docType, setDocType] = React.useState("");
  const [assigned, setAssigned] = React.useState("");
  const [offset, setOffset] = React.useState(0);
  const params = { status, document_type: docType, assigned_to: assigned === "me" ? userId : "", limit: PAGE, offset, sort_by: "submitted_at", order: "asc" };
  const q = useQuery({
    queryKey: qk.reviewQueue(params),
    queryFn: ({ signal }) => apiRequest<ReviewQueueItem[]>("/idp/review-queue", { query: params, signal }),
    placeholderData: keepPreviousData,
    refetchInterval: 30_000,
  });
  const items = q.data?.data ?? [];
  const pg = q.data?.meta?.pagination;
  const total = pg?.total ?? items.length;
  const filtered = Boolean(status || docType || assigned);
  const set = (fn: (v: string) => void) => (e: React.ChangeEvent<HTMLSelectElement>) => { fn(e.target.value); setOffset(0); };
  const age = (h: number) => (h >= 48 ? t("dashboard.ageDays", { days: Math.floor(h / 24) }) : t("dashboard.age", { hours: Math.floor(h) }));

  return (
    <div className="mx-auto flex max-w-[1400px] flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">{t("idp.queueTitle")}</h1>
          <p className="text-sm text-muted-foreground" data-testid="queue-count">{t("idp.queueSubtitle", { count: total })}</p>
        </div>
        <UploadButton />
      </div>
      <Card className="flex flex-wrap items-end gap-3 p-3" data-testid="queue-filters">
        <div className="flex flex-col gap-1">
          <Label htmlFor="f-status">{t("idp.filter.status")}</Label>
          <NativeSelect id="f-status" value={status} onChange={set(setStatus)}>
            <option value="">{t("idp.filter.all")}</option>
            {QUEUE_STATUSES.map((s) => <option key={s} value={s}>{t(`idp.status.${s}`)}</option>)}
          </NativeSelect>
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor="f-type">{t("idp.filter.docType")}</Label>
          <NativeSelect id="f-type" value={docType} onChange={set(setDocType)}>
            <option value="">{t("idp.filter.all")}</option>
            {DOC_TYPES.map((d) => <option key={d} value={d}>{t(`idp.docType.${d}`)}</option>)}
          </NativeSelect>
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor="f-assigned">{t("idp.filter.assigned")}</Label>
          <NativeSelect id="f-assigned" value={assigned} onChange={set(setAssigned)}>
            <option value="">{t("idp.filter.all")}</option>
            <option value="me">{t("idp.filter.me")}</option>
          </NativeSelect>
        </div>
        {filtered && <Button variant="ghost" size="sm" onClick={() => { setStatus(""); setDocType(""); setAssigned(""); setOffset(0); }}>{t("buttons.clearFilters")}</Button>}
      </Card>
      {q.isError && <p role="alert" className="text-sm text-danger">{t("errors.generic")} <Button size="sm" variant="outline" onClick={() => void q.refetch()}>{t("buttons.retry")}</Button></p>}
      {q.isPending && <div className="h-40 animate-pulse rounded-lg bg-muted" />}
      {q.isSuccess && items.length === 0 && (
        <Card className="flex flex-col items-center gap-3 p-10 text-center" data-testid="queue-empty">
          <Inbox className="h-10 w-10 text-muted-foreground" aria-hidden />
          <p className="font-medium">{t("idp.empty")}</p>
          <p className="text-sm text-muted-foreground">{t("idp.emptyHint")}</p>
          <UploadButton />
        </Card>
      )}
      {items.length > 0 && (
        <Card className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-sm" data-testid="queue-table">
            <thead className="border-b bg-muted/50 text-left text-xs text-muted-foreground">
              <tr>
                {(["filename", "type", "confidence", "critical", "assigned", "age", "actions"] as const).map((c) => (
                  <th key={c} scope="col" className="px-3 py-2 font-medium">{t(`idp.col.${c}`)}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {items.map((it) => (
                <tr key={it.document_id} data-testid="queue-row" data-document-id={it.document_id} className="hover:bg-muted/40">
                  <td className="max-w-[280px] truncate px-3 py-2 font-medium" title={it.filename ?? ""}>{it.filename ?? "—"}</td>
                  <td className="px-3 py-2">{t(`idp.docType.${it.document_type ?? "unknown"}` as "idp.docType.OTHER")}</td>
                  <td className="px-3 py-2"><ConfidenceBadge value={it.confidence_avg} /></td>
                  <td className="px-3 py-2 tabular-nums">{it.critical_fields_count > 0 ? <Badge variant="danger">{formatNumber(it.critical_fields_count, locale, 0)}</Badge> : "0"}</td>
                  <td className="px-3 py-2">{it.assigned_to ? (it.assigned_to === userId ? t("idp.filter.me") : `${it.assigned_to.slice(0, 8)}…`) : <span className="text-muted-foreground">{t("idp.unassigned")}</span>}</td>
                  <td className="px-3 py-2 tabular-nums text-muted-foreground">{age(it.age_hours)}</td>
                  <td className="px-3 py-2">
                    <Link href={`/idp/review/${it.document_id}`} className={buttonVariants({ size: "sm" })} data-testid="review-link">{t("buttons.review")}</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
      {total > PAGE && (
        <div className="flex items-center justify-end gap-3 text-sm" data-testid="pagination">
          <span className="tabular-nums text-muted-foreground">{t("idp.pageInfo", { from: offset + 1, to: Math.min(offset + PAGE, total), total })}</span>
          <Button size="sm" variant="outline" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE))}>{t("buttons.previous")}</Button>
          <Button size="sm" variant="outline" disabled={!pg?.has_next} onClick={() => setOffset(offset + PAGE)}>{t("buttons.next")}</Button>
        </div>
      )}
    </div>
  );
}

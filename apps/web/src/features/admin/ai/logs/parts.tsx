"use client";
import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { Copy } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import { apiRequest, type Pagination } from "@/lib/api-client";
import { qk } from "@/lib/query-keys";

/** `request_id` with a copy button (SCR-65). */
export function RequestId({ id, onFilter }: { id: string | null | undefined; onFilter?: (id: string) => void }) {
  const t = useTranslations("aiLogs");
  const toast = useToast();
  if (!id) return <span>—</span>;
  return (
    <span className="inline-flex items-center gap-1">
      <button type="button" className="font-mono text-xs hover:underline" onClick={(e) => { e.stopPropagation(); onFilter?.(id); }} title={t("filterBy")} data-testid="log-request-id">{id.slice(0, 13)}…</button>
      <button type="button" aria-label={t("copy")} className="rounded p-0.5 text-muted-foreground hover:bg-muted" data-testid="log-copy"
        onClick={(e) => { e.stopPropagation(); void navigator.clipboard?.writeText(id).then(() => toast.push(t("copied"), "success"), () => undefined); }}>
        <Copy className="h-3 w-3" aria-hidden />
      </button>
    </span>
  );
}

export function Pager({ pagination, offset, onOffset, limit }: { pagination?: Pagination | null; offset: number; limit: number; onOffset: (o: number) => void }) {
  const t = useTranslations("aiLogs");
  if (!pagination) return null;
  return (
    <div className="flex items-center justify-between text-sm text-muted-foreground">
      <span data-testid="log-total">{t("total", { total: pagination.total })}</span>
      <div className="flex gap-2">
        <Button size="sm" variant="outline" disabled={offset === 0} onClick={() => onOffset(Math.max(0, offset - limit))} data-testid="log-prev">{t("prev")}</Button>
        <Button size="sm" variant="outline" disabled={!pagination.has_next} onClick={() => onOffset(offset + limit)} data-testid="log-next">{t("next")}</Button>
      </div>
    </div>
  );
}

/** User names for the "người được phục vụ" column (EP-ADM-05, `platform:read` — ADM/CEO have it). */
export function useUserNames(): (id: string | null | undefined) => string {
  const users = useQuery({
    queryKey: qk.users({ purpose: "ai-logs" }),
    queryFn: () => apiRequest<{ id: string; full_name: string; email: string }[]>("/platform/users", { query: { limit: 100 } }).then((r) => r.data),
    staleTime: 300_000,
  });
  return React.useCallback((id) => {
    if (!id) return "—";
    return users.data?.find((u) => u.id === id)?.full_name ?? `${id.slice(0, 8)}…`;
  }, [users.data]);
}

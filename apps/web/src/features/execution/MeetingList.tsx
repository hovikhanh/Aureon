"use client";
import { useQuery } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { FileText } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { QueryError } from "@/components/QueryError";
import { apiRequest } from "@/lib/api-client";
import { formatDate, type AppLocale } from "@/lib/format";

interface MeetingOut { id: string; title: string; held_at: string; summary: string | null; source_document_id: string | null }

/** Recent meetings of SCR-44 — EP-EXE-03 `GET /execution/meetings` (scope by the API), newest first, with the AI summary (ENT-MeetingSummary). */
export function MeetingList() {
  const t = useTranslations("meetings.list");
  const locale = useLocale() as AppLocale;
  const q = useQuery({
    queryKey: ["execution", "meetings", "recent"],
    queryFn: ({ signal }) => apiRequest<MeetingOut[]>("/execution/meetings", { query: { limit: 20, sort_by: "held_at", order: "desc" }, signal }),
  });
  const rows = q.data?.data ?? [];
  return (
    <Card data-testid="meeting-list">
      <CardHeader><CardTitle>{t("title")}</CardTitle></CardHeader>
      <CardContent>
        {q.isPending && <div className="h-16 animate-pulse rounded bg-muted" />}
        {q.isError && <QueryError error={q.error} onRetry={() => void q.refetch()} testId="meeting-list-error" />}
        {q.isSuccess && rows.length === 0 && <p className="text-sm text-muted-foreground">{t("empty")}</p>}
        <ul className="divide-y">
          {rows.map((m) => (
            <li key={m.id} className="py-3" data-testid="meeting-row">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <span className="font-medium">{m.title}</span>
                <span className="text-xs text-muted-foreground tabular-nums">{formatDate(m.held_at, locale)}</span>
              </div>
              <p className="mt-1 text-sm text-muted-foreground">{m.summary ?? t("noSummary")}</p>
              {m.source_document_id && <span className="mt-1 inline-flex items-center gap-1 text-xs text-muted-foreground"><FileText className="h-3 w-3" aria-hidden />{t("fromDocument")}</span>}
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

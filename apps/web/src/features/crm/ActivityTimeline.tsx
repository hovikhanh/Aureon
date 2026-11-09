"use client";
/**
 * Sales activity timeline (R-DEC-176, EP-SAL-12) for Account 360 and the opportunity detail:
 * newest first, with an "add" button that opens the generic record form preset to the record.
 */
import { useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { QueryError } from "@/components/QueryError";
import { QuickCreate, type RecordCaps } from "@/features/records/RecordCrud";
import { formatDateTime, type AppLocale } from "@/lib/format";
import { crmKeys, useActivities } from "./use-crm";

export function ActivityTimeline({ query, caps, defaults, testId }: {
  query: Record<string, string>; caps: RecordCaps; defaults: Record<string, string>; testId: string;
}) {
  const t = useTranslations();
  const locale = useLocale() as AppLocale;
  const qc = useQueryClient();
  const acts = useActivities(query);
  const label = (group: string, v: string) => {
    const key = `records.enum.${group}.${v}`;
    return t.has(key) ? t(key as "crm.me") : v;
  };
  return (
    <Card className="p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-semibold">{t("crm.activities")}</h2>
        <QuickCreate resource="activities" caps={caps} defaults={defaults} testId={`${testId}-add`}
          onCreated={() => void qc.invalidateQueries({ queryKey: crmKeys.all })} />
      </div>
      {acts.isError && <QueryError error={acts.error} />}
      {acts.isSuccess && acts.data.length === 0 && <p className="mt-2 text-sm text-muted-foreground">{t("crm.noActivities")}</p>}
      <ol className="mt-2 flex flex-col gap-2 text-sm" data-testid={testId}>
        {(acts.data ?? []).map((a) => (
          <li key={a.id} className="border-l-2 border-primary/40 pl-2" data-testid="activity-item">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="outline">{label("type", a.type)}</Badge>
              <span className="font-medium">{a.subject}</span>
              <Badge variant={a.status === "completed" ? "success" : a.status === "cancelled" ? "danger" : "default"}>{label("status", a.status)}</Badge>
            </div>
            <div className="text-xs text-muted-foreground tabular-nums">{a.code} · {formatDateTime(a.start_at, locale)}</div>
            {a.outcome && <p className="text-xs">{t("crm.outcome")}: {a.outcome}</p>}
            {a.next_action && <p className="text-xs">{t("crm.nextAction")}: {a.next_action}</p>}
          </li>
        ))}
      </ol>
    </Card>
  );
}

"use client";
/**
 * SCR-49 Decision Log panel (M3.3, EP-43, 03 §3.5): a list of decisions with status, decided date
 * and review date; review-due rows are highlighted; a toggle filters to the follow-up queue only.
 */
import { useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import type { Api } from "@aureon/shared-types";
import { Card } from "@/components/ui/card";
import { QueryError } from "@/components/QueryError";
import { Badge, type BadgeProps } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatDate, type AppLocale } from "@/lib/format";
import { byDecidedDesc, nextReview, reviewDue } from "./decisions";
import { useDecisions } from "./use-knowledge";

const STATUS_VARIANT: Record<string, BadgeProps["variant"]> = {
  open: "primary",
  in_progress: "ai",
  done: "success",
  cancelled: "default",
};

export function DecisionsPanel() {
  const t = useTranslations("decisions");
  const locale = useLocale() as AppLocale;
  const [dueOnly, setDueOnly] = useState(false);
  const q = useDecisions({ reviewDue: dueOnly });

  return (
    <div className="flex flex-col gap-4" data-testid="decisions-panel">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold">{t("title")}</h2>
        <Button
          size="sm"
          variant={dueOnly ? "default" : "outline"}
          aria-pressed={dueOnly}
          data-testid="decisions-due-toggle"
          onClick={() => setDueOnly((v) => !v)}
        >
          {t("reviewDueFilter")}
        </Button>
      </div>

      {q.isLoading && <p className="text-sm text-muted-foreground">{t("loading")}</p>}
      {q.isError && <QueryError error={q.error} onRetry={() => void q.refetch()} />}
      {q.data && q.data.data.length === 0 && (
        <p className="text-sm text-muted-foreground" data-testid="decisions-empty">{t("empty")}</p>
      )}

      {q.data && q.data.data.length > 0 && (
        <ul className="flex flex-col gap-2">
          {byDecidedDesc(q.data.data).map((d) => (
            <DecisionRow key={d.id} d={d} locale={locale} />
          ))}
        </ul>
      )}
    </div>
  );
}

function DecisionRow({ d, locale }: { d: Api.DecisionOut; locale: AppLocale }) {
  const t = useTranslations("decisions");
  const due = reviewDue(d);
  const review = nextReview(d);
  return (
    <li>
      <Card
        className={due ? "border-warning/60 bg-warning-subtle/40 p-4" : "p-4"}
        data-testid="decision-row"
        data-review-due={due}
      >
        <div className="flex flex-wrap items-start justify-between gap-2">
          <p className="font-medium">{d.content}</p>
          <Badge variant={STATUS_VARIANT[d.status] ?? "default"}>{t(`status.${d.status}`)}</Badge>
        </div>
        <div className="mt-2 flex flex-wrap gap-x-6 gap-y-1 text-xs text-muted-foreground">
          <span>{t("decidedAt", { date: formatDate(d.decided_at, locale) })}</span>
          {review && (
            <span data-testid="decision-review">
              {t("nextReview", { date: formatDate(review, locale) })}
            </span>
          )}
          {due && (
            <Badge variant="warning" data-testid="decision-due-chip">{t("dueChip")}</Badge>
          )}
        </div>
      </Card>
    </li>
  );
}

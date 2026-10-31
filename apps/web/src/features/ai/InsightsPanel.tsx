"use client";
/**
 * Executive insights panel (06 §3.4, EP-AI-05): lists the 9-part AI insights for the viewer's
 * audience via `GET /ai/insights`, each rendered as an InsightCard with grounded evidence and a
 * "Tại sao?" expander (R-DEC-107/112). Loading / error / empty are handled locally (FR-DSH-07).
 */
import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import type { Api } from "@aureon/shared-types";
import { api } from "@/lib/api-client";
import { InsightCard } from "@/components/ai/InsightCard";

export function InsightsPanel() {
  const t = useTranslations("insight");
  const q = useQuery({
    queryKey: ["ai", "insights"],
    queryFn: ({ signal }) => api.get<Api.InsightOut[]>("/ai/insights", undefined, signal),
    staleTime: 60_000,
  });
  return (
    <section className="flex flex-col gap-3" data-testid="insights-panel">
      <h2 className="text-sm font-semibold text-muted-foreground">{t("sectionTitle")}</h2>
      {q.isLoading && <div className="h-24 animate-pulse rounded bg-muted" />}
      {q.isError && <p className="text-sm text-danger" data-testid="insights-error">{t("error")}</p>}
      {q.isSuccess && q.data.length === 0 && (
        <p className="text-sm text-muted-foreground" data-testid="insights-empty">{t("empty")}</p>
      )}
      {q.isSuccess && q.data.length > 0 && (
        <div className="grid gap-3 lg:grid-cols-2" data-testid="insights-list">
          {q.data.map((it) => (
            <InsightCard key={it.id} insight={it} />
          ))}
        </div>
      )}
    </section>
  );
}

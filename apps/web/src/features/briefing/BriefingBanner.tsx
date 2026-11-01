"use client";
/**
 * SCR-40 CEO Daily Briefing banner (M3.3, 03 §3.1) — a compact header card above the Executive
 * dashboard: summary line, generated time, opened indicator, and a stale-metric warning chip when
 * any metric is stale. Marks the briefing opened on mount (G1). On 403 (non-exec) or error it
 * renders nothing so the dashboard below still shows.
 */
import { useLocale, useTranslations } from "next-intl";
import { Bot, Clock } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatDateTime, type AppLocale } from "@/lib/format";
import { isOpened, openedAt, staleCount } from "./briefing";
import { useBriefingToday, useOpenBriefing } from "./use-briefing";

export function BriefingBanner() {
  const t = useTranslations("briefing");
  const locale = useLocale() as AppLocale;
  const q = useBriefingToday();
  useOpenBriefing(q.data);

  // Non-exec (403) or any error → render nothing; the dashboard below is independent.
  if (q.isError || !q.data) return null;
  const b = q.data;
  const stale = staleCount(b);
  const opened = isOpened(b);
  const openedIso = openedAt(b);

  return (
    <Card className="flex flex-col gap-2 border-ai/40 p-4" data-testid="briefing-banner">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h2 className="flex items-center gap-2 text-sm font-medium text-ai">
          <Bot className="h-4 w-4" aria-hidden />
          {t("title")}
        </h2>
        <Badge variant={opened ? "default" : "ai"} data-testid="briefing-opened">
          {opened && openedIso ? t("openedAt", { time: formatDateTime(openedIso, locale) }) : t("new")}
        </Badge>
      </div>
      <p className="text-base" data-testid="briefing-summary">{b.summary_line}</p>
      <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
        <span className="flex items-center gap-1">
          <Clock className="h-3.5 w-3.5" aria-hidden />
          {t("generatedAt", { time: formatDateTime(b.generated_at, locale) })}
        </span>
      </div>
      {stale > 0 && (
        <Badge variant="warning" data-testid="briefing-stale" className="self-start">
          {t("stale", { count: stale, codes: b.stale_metric_codes?.join(", ") ?? "" })}
        </Badge>
      )}
    </Card>
  );
}

"use client";
/**
 * "AI đã làm" feed (SCR `/ask/activity`, M3.2 R-DEC-130): a recap of the Autonomy-L3 actions the AI
 * executed for the viewer, newest first, each undoable for 24h (06 §5.1). Reuses `ActionCard` (the
 * L3 "AI đã làm" label + executed badge) and adds an inline Undo with the remaining-window hint.
 */
import * as React from "react";
import { useLocale, useTranslations } from "next-intl";
import { RotateCcw } from "lucide-react";
import { ActionCard } from "@/components/ai/ActionCard";
import { Button } from "@/components/ui/button";
import { formatDateTime, type AppLocale } from "@/lib/format";
import { feedActions, remainingLabel, remainingMs, undoable, type FeedAction } from "./ai-feed";
import { useAiFeed, useFeedUndo } from "./use-ai-feed";

export interface FeedViewer {
  id: string;
  permissions: string[];
}

export function AiFeed({ viewer }: { viewer: FeedViewer }) {
  const t = useTranslations("aiFeed");
  const locale = useLocale() as AppLocale;
  const q = useAiFeed();
  const { undo, busy } = useFeedUndo();
  const rows = React.useMemo(() => feedActions((q.data ?? []) as FeedAction[]), [q.data]);

  return (
    <section className="flex flex-col gap-3" data-testid="ai-feed">
      <header>
        <h1 className="text-lg font-semibold">{t("title")}</h1>
        <p className="text-sm text-muted-foreground">{t("subtitle")}</p>
      </header>
      {q.isError && (
        <p role="alert" className="text-sm text-danger">
          {t("error")}
        </p>
      )}
      {!q.isError && rows.length === 0 && (
        <p className="text-sm text-muted-foreground" data-testid="feed-empty">
          {t("empty")}
        </p>
      )}
      <ul className="flex flex-col gap-3">
        {rows.map((a) => {
          const canUndo = undoable(a);
          return (
            <li key={a.id}>
              <ActionCard
                action={a}
                viewerId={viewer.id}
                permissions={viewer.permissions}
                meta={
                  <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                    {a.executed_at && <span>{formatDateTime(a.executed_at, locale)}</span>}
                    {canUndo ? (
                      <>
                        <span data-testid="undo-window">
                          {t("undoWindow", { left: remainingLabel(remainingMs(a)) })}
                        </span>
                        <Button
                          variant="outline"
                          className="h-7 gap-1 px-2 text-xs"
                          disabled={busy === a.id}
                          onClick={() => undo(a.id)}
                          data-testid="feed-undo"
                        >
                          <RotateCcw className="h-3.5 w-3.5" aria-hidden />
                          {t("undo")}
                        </Button>
                      </>
                    ) : (
                      <span>{t("undoExpired")}</span>
                    )}
                  </div>
                }
              />
            </li>
          );
        })}
      </ul>
    </section>
  );
}

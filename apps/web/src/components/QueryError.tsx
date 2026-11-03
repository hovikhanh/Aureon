"use client";
import { useTranslations } from "next-intl";
import { Lock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { errorKind, errorText } from "@/lib/error-text";

/** Inline load error (FR-DSH-07: a widget fails in place): 403 → no-permission notice without a retry, else message + retry. */
export function QueryError({ error, onRetry, testId = "query-error" }: { error: unknown; onRetry?: () => void; testId?: string }) {
  const t = useTranslations();
  const kind = errorKind(error);
  return (
    <div role="alert" className={`flex items-center gap-3 rounded border p-3 text-sm ${kind === "forbidden" ? "border-border text-muted-foreground" : "border-danger/40 text-danger"}`} data-testid={testId} data-kind={kind}>
      {kind === "forbidden" && <Lock className="h-4 w-4 shrink-0" aria-hidden />}
      <span>{errorText(t, error)}</span>
      {onRetry && kind !== "forbidden" && kind !== "notFound" && <Button size="sm" variant="outline" onClick={onRetry}>{t("buttons.retry")}</Button>}
    </div>
  );
}

"use client";

import { AlertTriangle } from "lucide-react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";

/**
 * Error state (06 §3.2): a plain-language message + a Retry button. The message is keyed so the
 * caller can map `error.code` (10 §1) to specific copy; `stale` adds the "data may be outdated"
 * note (06 §3.2, keep old data if present). `role="alert"` + icon + text, not color only (06 §9).
 */
export function ErrorState({
  title,
  description,
  onRetry,
  stale = false,
  className,
}: {
  /** Optional override; defaults to `states.error.title`. */
  title?: string;
  /** Optional override; defaults to `states.error.description`. */
  description?: string;
  /** Retry callback; the button is rendered only when provided. */
  onRetry?: () => void;
  /** When true, show the "data may be outdated" note (stale-while-error). */
  stale?: boolean;
  className?: string;
}) {
  const t = useTranslations("states.error");
  return (
    <div
      role="alert"
      className={cn(
        "flex flex-col items-center justify-center gap-3 rounded-lg border border-border p-10 text-center",
        className,
      )}
    >
      <AlertTriangle aria-hidden="true" className="h-10 w-10 text-status-critical" />
      <h2 className="text-h3 text-foreground">{title ?? t("title")}</h2>
      <p className="max-w-md text-body text-muted-foreground">{description ?? t("description")}</p>
      {stale ? <p className="text-caption text-status-warn">{t("stale")}</p> : null}
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="mt-2 inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-body font-medium text-primary-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
        >
          {t("retry")}
        </button>
      ) : null}
    </div>
  );
}

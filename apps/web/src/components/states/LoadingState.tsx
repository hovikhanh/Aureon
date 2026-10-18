import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";

/**
 * Loading state (06 §3.2): content-shaped skeleton, never a full-page spinner.
 * Marked `aria-busy` with an `aria-live="polite"` status so screen readers announce loading
 * without spamming; visual skeleton bars are `aria-hidden` (06 §9 live-region guidance).
 */
export function LoadingState({
  className,
  rows = 3,
  label,
}: {
  className?: string;
  /** Number of skeleton bars; default approximates a card/list shape. */
  rows?: number;
  /** Optional override for the announced label (defaults to `states.loading.label`). */
  label?: string;
}) {
  const t = useTranslations("states.loading");
  return (
    <div
      className={cn("flex flex-col gap-3", className)}
      role="status"
      aria-busy="true"
      aria-live="polite"
    >
      <span className="sr-only">{label ?? t("label")}</span>
      <div aria-hidden="true" className="flex flex-col gap-3">
        {Array.from({ length: rows }).map((_, index) => (
          <div
            key={index}
            className="h-6 animate-pulse rounded-md bg-neutral-200"
            style={{ width: `${100 - index * 12}%` }}
          />
        ))}
      </div>
    </div>
  );
}

import type { ReactNode } from "react";
import { Inbox } from "lucide-react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";

/**
 * Empty state (06 §3.2): light illustration (icon) + one explanatory sentence + a primary
 * action. Icon is decorative (`aria-hidden`); meaning comes from text, not color (06 §9).
 */
export function EmptyState({
  title,
  description,
  action,
  className,
}: {
  /** Optional override; defaults to `states.empty.title`. */
  title?: string;
  /** Optional override; defaults to `states.empty.description`. */
  description?: string;
  /** Primary action (e.g. a link to SCR-08 Upload). */
  action?: ReactNode;
  className?: string;
}) {
  const t = useTranslations("states.empty");
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-border p-10 text-center",
        className,
      )}
    >
      <Inbox aria-hidden="true" className="h-10 w-10 text-neutral-400" />
      <h2 className="text-h3 text-foreground">{title ?? t("title")}</h2>
      <p className="max-w-md text-body text-muted-foreground">{description ?? t("description")}</p>
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  );
}

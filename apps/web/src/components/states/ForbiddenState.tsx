import type { ReactNode } from "react";
import { ShieldAlert } from "lucide-react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";

/**
 * Forbidden (403) state (06 §3.2 / 02 §4.1 item 4): never a silent hide — explicitly tell the
 * user the content is out of their scope. `role="alert"` + icon + text, not color only (06 §9).
 */
export function ForbiddenState({
  title,
  description,
  action,
  className,
}: {
  /** Optional override; defaults to `states.forbidden.title`. */
  title?: string;
  /** Optional override; defaults to `states.forbidden.description`. */
  description?: string;
  /** Optional action (e.g. a link back to the user's home route). */
  action?: ReactNode;
  className?: string;
}) {
  const t = useTranslations("states.forbidden");
  return (
    <div
      role="alert"
      className={cn(
        "flex flex-col items-center justify-center gap-3 rounded-lg border border-border p-10 text-center",
        className,
      )}
    >
      <ShieldAlert aria-hidden="true" className="h-10 w-10 text-status-warn" />
      <h2 className="text-h3 text-foreground">{title ?? t("title")}</h2>
      <p className="max-w-md text-body text-muted-foreground">{description ?? t("description")}</p>
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  );
}

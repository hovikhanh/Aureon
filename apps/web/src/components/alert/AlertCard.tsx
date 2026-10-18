import type { ComponentType } from "react";
import Link from "next/link";
import { OctagonAlert, Sparkles, TriangleAlert } from "lucide-react";
import { useTranslations } from "next-intl";
import type { AlertSeverity } from "@aureon/shared-types";
import type { AlertCardProps } from "@/features/dashboard/types";
import { useP04Formatter } from "@/lib/use-p04-formatter";
import { cn } from "@/lib/utils";

/**
 * AlertCard — "Cần anh/chị quyết" item on SCR-01..04 (06 §4.1, §6.6; AlertOut 10 §3).
 *
 * Severity is shown with icon + text + color, never color alone (06 §4.1, §9):
 *  - CRITICAL → ⛔ + "Nguy cấp", status-critical accent + left border.
 *  - WARNING  → ⚠ + "Cảnh báo", status-warn accent + left border.
 *
 * The card title links through to SCR-09 filtered by the alert condition (P01). The
 * AI-suggested action (06 §6.3 L1) is AI content, so it uses the `--ai` token family — never
 * `--primary`. The acknowledge button is a user action and uses `--primary`. All copy is i18n
 * (06 §7.2, TC-UI-005); times/periods use the P04 formatter (06 §7.1).
 */
interface SeverityStyle {
  labelKey: "WARNING" | "CRITICAL";
  icon: ComponentType<{ className?: string; "aria-hidden"?: boolean | "true" | "false" }>;
  accent: string;
  border: string;
}

const SEVERITY_STYLE: Record<AlertSeverity, SeverityStyle> = {
  CRITICAL: {
    labelKey: "CRITICAL",
    icon: OctagonAlert,
    accent: "text-status-critical",
    border: "border-l-status-critical",
  },
  WARNING: {
    labelKey: "WARNING",
    icon: TriangleAlert,
    accent: "text-status-warn",
    border: "border-l-status-warn",
  },
};

export function AlertCard(props: AlertCardProps) {
  const {
    alertCode,
    metricCode,
    severity,
    titleI18nKey,
    suggestedActionI18nKey,
    periodKey,
    triggeredAt,
    href,
    canAcknowledge,
    onAcknowledge,
  } = props;

  const t = useTranslations("alert");
  const tRoot = useTranslations();
  const fmt = useP04Formatter();
  const style = SEVERITY_STYLE[severity];
  const SeverityIcon = style.icon;

  const title = titleI18nKey && tRoot.has(titleI18nKey) ? tRoot(titleI18nKey) : alertCode;
  const suggestedAction =
    suggestedActionI18nKey && tRoot.has(suggestedActionI18nKey)
      ? tRoot(suggestedActionI18nKey)
      : null;
  const severityLabel = t(`severity.${style.labelKey}`);

  return (
    <div
      role="group"
      aria-label={`${severityLabel}: ${title}`}
      data-alert-code={alertCode}
      data-severity={severity}
      className={cn(
        "flex flex-col gap-2 rounded-lg border border-l-4 bg-card p-4 text-card-foreground",
        style.border,
      )}
    >
      {/* Severity badge (icon + text) + metric id + period */}
      <div className="flex items-center justify-between gap-2">
        <span className={cn("inline-flex items-center gap-1 text-caption font-medium", style.accent)}>
          <SeverityIcon aria-hidden="true" className="h-4 w-4" />
          <span>{severityLabel}</span>
        </span>
        <span className="font-data text-caption text-neutral-500">
          {metricCode} · {fmt.period(periodKey)}
        </span>
      </div>

      {/* Title → drill-down link (P01, → SCR-09 filtered). */}
      <Link
        href={href}
        aria-label={t("viewDetail", { name: title })}
        className="text-h3 text-foreground underline-offset-2 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
      >
        {title}
      </Link>

      {/* AI-suggested action (06 §6.3 L1) — AI content, uses the --ai family. */}
      {suggestedAction ? (
        <div className="flex items-start gap-1.5 rounded-md bg-ai-muted p-2 text-ai-muted-foreground">
          <Sparkles aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0" />
          <p className="text-caption">
            <span className="font-medium">{t("suggestedAction")}: </span>
            {suggestedAction}
          </p>
        </div>
      ) : null}

      <p className="text-caption text-neutral-500">
        {t("triggeredAt", { time: fmt.dateTime(triggeredAt) })}
      </p>

      {/* Acknowledge — user action, uses --primary (06 §6.3). */}
      {canAcknowledge && onAcknowledge ? (
        <button
          type="button"
          onClick={onAcknowledge}
          className="mt-1 inline-flex w-fit items-center justify-center rounded-md bg-primary px-3 py-1.5 text-caption font-medium text-primary-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
        >
          {t("acknowledge")}
        </button>
      ) : null}
    </div>
  );
}

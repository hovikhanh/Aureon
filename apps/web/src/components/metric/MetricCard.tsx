import type { ComponentType } from "react";
import Link from "next/link";
import { CircleCheck, OctagonAlert, TrendingDown, TrendingUp, TriangleAlert } from "lucide-react";
import { useTranslations } from "next-intl";
import type { MetricStatusColor } from "@aureon/shared-types";
import type { MetricCardProps } from "@/features/dashboard/types";
import { isMaskedValue } from "@/features/dashboard/types";
import { formatMetricValue } from "@/features/dashboard/format-metric";
import { useP04Formatter } from "@/lib/use-p04-formatter";
import { cn } from "@/lib/utils";
import { MaskedValue } from "./MaskedValue";

/**
 * MetricCard — the KPI card used across SCR-01..04 (06 §4.1, §6.6).
 *
 * States (06 §4.1 / 10 §1.9), meaning conveyed by icon + text + color (NOT color alone, 06 §9):
 *  - OK + GREEN  → value + "Bình thường" (ok icon), status-ok accent.
 *  - OK + YELLOW → value + "Cảnh báo" (⚠ icon), status-warn accent + border.
 *  - OK + RED    → value + "Nguy cấp" (⛔ icon), status-critical accent + border.
 *  - NO_DATA     → `—` + "Chưa có dữ liệu nguồn", NO threshold color, no fake 0.
 *  - NOT_COMPUTABLE → `N/A` + "Không tính được" + reason tooltip, NO threshold color.
 *  - display_hint GT_24_MONTHS (OK, value=null) → `> 24 tháng` (03 FIN-03).
 *  - masked salary (`value = { masked: true }`) → `••••` via MaskedValue (06 §7.4, DS3).
 *
 * P01 (every number traceable): the value is a drill-down link (`href` → SCR-09) with an
 * accessible name. All numbers go through the P04 formatter (06 §7.1); nothing is formatted
 * by hand. No Vietnamese literal lives here — all copy is i18n (06 §7.2, TC-UI-005).
 */
interface StatusStyle {
  labelKey: "ok" | "warning" | "critical";
  icon: ComponentType<{ className?: string; "aria-hidden"?: boolean | "true" | "false" }>;
  /** Icon/text color class (status family — only used for OK values). */
  accent: string;
  /** Card border accent for warning/critical (06 §4.1 "viền vàng/đỏ"). */
  border: string;
}

const STATUS_STYLE: Record<MetricStatusColor, StatusStyle> = {
  GREEN: {
    labelKey: "ok",
    icon: CircleCheck,
    accent: "text-status-ok",
    border: "border-border",
  },
  YELLOW: {
    labelKey: "warning",
    icon: TriangleAlert,
    accent: "text-status-warn",
    border: "border-status-warn",
  },
  RED: {
    labelKey: "critical",
    icon: OctagonAlert,
    accent: "text-status-critical",
    border: "border-status-critical",
  },
};

export function MetricCard(props: MetricCardProps) {
  const {
    metricCode,
    nameI18nKey,
    formatKind,
    valueState,
    value,
    statusColor,
    notComputableReason,
    displayHint,
    periodKey,
    deltaRatio,
    formulaDisplay,
    href,
    computedAt,
  } = props;

  const t = useTranslations("metric");
  // Root translator for resolving the metric name key (`metric.<CODE>.name`, 06 §7.2),
  // which is supplied by data (T-111). Missing → fall back to the technical code.
  const tRoot = useTranslations();
  const fmt = useP04Formatter();
  const units = {
    days: t("unit.days"),
    months: t("unit.months"),
    tasksPerPerson: t("unit.tasksPerPerson"),
    vndPerPerson: t("unit.vndPerPerson"),
  };

  const masked = isMaskedValue(value);
  const periodLabel = fmt.period(periodKey);
  // Resolve the human metric name, falling back to the code if the key is unknown.
  const name = nameI18nKey && tRoot.has(nameI18nKey) ? tRoot(nameI18nKey) : metricCode;

  // ── Decide what the value area renders and whether a threshold color applies. ──────────
  const isOk = valueState === "OK";
  const status = isOk && statusColor ? STATUS_STYLE[statusColor] : null;

  let valueNode: React.ReactNode;
  let valueText: string; // plain text for the accessible link name
  if (masked) {
    valueNode = <MaskedValue value={value} />;
    valueText = t("masked.label");
  } else if (isOk && displayHint === "GT_24_MONTHS") {
    valueText = t("displayHint.GT_24_MONTHS");
    valueNode = valueText;
  } else if (isOk && typeof value === "number") {
    valueText = formatMetricValue(fmt, formatKind, value, units);
    valueNode = valueText;
  } else if (valueState === "NOT_COMPUTABLE") {
    // ASCII "N/A" marker (06 §4.1); descriptive text + reason carry the meaning.
    valueText = "N/A";
    valueNode = valueText;
  } else {
    // NO_DATA (or OK with a null value and no hint) → neutral placeholder, never a fake 0.
    valueText = fmt.number(null); // → `—` placeholder from i18n
    valueNode = valueText;
  }

  const notComputable = valueState === "NOT_COMPUTABLE";
  const noData = valueState === "NO_DATA";
  const reasonText =
    notComputable && notComputableReason ? t(`notComputableReason.${notComputableReason}`) : null;

  return (
    <div
      className={cn(
        "flex flex-col gap-2 rounded-lg border bg-card p-4 text-card-foreground",
        status ? status.border : "border-border",
      )}
      data-metric-code={metricCode}
      data-value-state={valueState}
      data-status-color={isOk && statusColor ? statusColor : undefined}
    >
      {/* Header: metric name + technical id + period */}
      <div className="flex items-baseline justify-between gap-2">
        <h3 className="text-h3 text-foreground">{name}</h3>
        <span className="font-data text-caption text-neutral-500">{metricCode}</span>
      </div>
      <p className="text-caption text-muted-foreground">
        {t("period")}: {periodLabel}
      </p>

      {/* Value — a drill-down link (P01). Accessible name = metric name + value. */}
      <Link
        href={href}
        aria-label={`${t("viewDetail", { name })} — ${valueText}`}
        className="group inline-flex w-fit items-center gap-2 rounded-md focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
      >
        <span
          className={cn(
            "font-data text-display tabular-nums group-hover:underline",
            status ? status.accent : "text-foreground",
          )}
        >
          {valueNode}
        </span>
      </Link>

      {/* Status / state line — icon + text, never color alone (06 §4.1, §9). */}
      {status ? (
        <p className={cn("inline-flex items-center gap-1 text-caption font-medium", status.accent)}>
          <status.icon aria-hidden="true" className="h-4 w-4" />
          <span>{t(`status.${status.labelKey}`)}</span>
        </p>
      ) : null}
      {noData ? <p className="text-caption text-neutral-500">{t("state.noData")}</p> : null}
      {notComputable ? (
        <p
          className="inline-flex items-center gap-1 text-caption text-neutral-500"
          title={reasonText ?? undefined}
        >
          <TriangleAlert aria-hidden="true" className="h-4 w-4" />
          <span>{t("state.notComputable")}</span>
          {reasonText ? <span className="sr-only">{reasonText}</span> : null}
        </p>
      ) : null}

      {/* Delta vs previous period (signed percent). */}
      {!masked && isOk && typeof deltaRatio === "number" ? (
        <p className="inline-flex items-center gap-1 text-caption text-neutral-600">
          {deltaRatio >= 0 ? (
            <TrendingUp aria-hidden="true" className="h-4 w-4" />
          ) : (
            <TrendingDown aria-hidden="true" className="h-4 w-4" />
          )}
          <span className="sr-only">{t("delta")}: </span>
          <span className="tabular-nums">{fmt.percentChange(deltaRatio)}</span>
        </p>
      ) : null}

      {/* Formula caption (P01) + freshness. */}
      {formulaDisplay ? (
        <p className="text-caption text-neutral-500">
          {t("formula")}: <span className="font-data">{formulaDisplay}</span>
        </p>
      ) : null}
      {computedAt ? (
        <p className="text-caption text-neutral-500">
          {t("freshness", { time: fmt.dateTime(computedAt) })}
        </p>
      ) : null}
    </div>
  );
}

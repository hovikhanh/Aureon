/**
 * UI prop types for the dashboard presentation components (T-109/T-110).
 *
 * These mirror the API response shapes in docs/3.EXECUTION/10-API-SPECIFICATION.md §3
 * (MetricValueOut, AlertOut, EP-12 `history[]`) so that T-111 can feed real/mock API data
 * straight into these components. The wire DTOs themselves live in `@aureon/shared-types`
 * (the single source of truth); this file only derives the UI-facing prop subsets and the
 * discriminated masked-value shape used by MetricCard / MaskedValue (10 §1.8 DS3).
 */
import type {
  AIStateLevel,
  AlertSeverity,
  MetricDisplayHint,
  MetricHistoryPoint,
  MetricStatusColor,
  MetricUnit,
  MetricValueState,
  NotComputableReason,
  Pillar,
} from "@aureon/shared-types";

export type { AIStateLevel, AlertSeverity, MetricUnit, Pillar };

/**
 * How a numeric metric value should be rendered via the P04 formatter (06 §7.1).
 * Derived from `MetricValueOut.unit` + `display_hint`; T-111 maps unit → formatKind.
 * - `compactCurrency`: VND money on a card/axis (`8,4 tỷ`, `850 tr`) — unit `VND`.
 * - `percent`: ratio → `12,5%` — unit `PERCENT`.
 * - `days`: whole days → `52 ngày` (unit suffix via i18n) — unit `DAYS`.
 * - `months`: 1-decimal months → `7,5 tháng` — unit `MONTHS`.
 * - `multiple`: `2,8x` — unit `RATIO`.
 * - `count`: plain integer — unit `COUNT`.
 * - `score`: 1-decimal score — unit `SCORE`.
 * - `tasksPerPerson` / `vndPerPerson`: plain number + i18n unit suffix.
 */
export type MetricFormatKind =
  | "compactCurrency"
  | "percent"
  | "days"
  | "months"
  | "multiple"
  | "count"
  | "score"
  | "tasksPerPerson"
  | "vndPerPerson";

/** Default `unit` → `MetricFormatKind` mapping (05 §4 `metric_unit`). */
export const UNIT_FORMAT_KIND: Record<MetricUnit, MetricFormatKind> = {
  VND: "compactCurrency",
  PERCENT: "percent",
  DAYS: "days",
  MONTHS: "months",
  RATIO: "multiple",
  COUNT: "count",
  SCORE: "score",
  TASKS_PER_PERSON: "tasksPerPerson",
  VND_PER_PERSON: "vndPerPerson",
};

/** A masked sensitive value (salary) — 10 §1.8 DS3: never carries a real `value`. */
export interface MaskedMetricValue {
  masked: true;
}

/** Type guard: does this value prop represent a masked (salary) field? */
export function isMaskedValue(value: unknown): value is MaskedMetricValue {
  return typeof value === "object" && value !== null && (value as MaskedMetricValue).masked === true;
}

/**
 * Props for `<MetricCard>` (06 §4.1 / §6.6). A card is either an ordinary metric value
 * (possibly `NO_DATA` / `NOT_COMPUTABLE`) or a masked salary field (`value: { masked: true }`).
 * Every number is a drill-down link to its source (P01) via `href` (→ SCR-09).
 */
export interface MetricCardProps {
  /** `metrics.code`, e.g. `METRIC-FIN-01` — shown as the technical id + used for i18n name. */
  metricCode: string;
  /** i18n key for the human metric name (06 §7.2: `metric.<CODE>.name`); falls back to code. */
  nameI18nKey?: string;
  pillar: Pillar;
  /** How to render the number (derived from `unit` / `display_hint`). */
  formatKind: MetricFormatKind;
  /** Current value state (10 §1.9). Omit/`OK` for a normal value. */
  valueState: MetricValueState;
  /**
   * The numeric value, or a masked marker `{ masked: true }`. `null`/omitted with
   * `valueState` NO_DATA/NOT_COMPUTABLE renders the N/A placeholder — never a fake 0.
   */
  value: number | null | MaskedMetricValue;
  /** Threshold color (10 §1.9); only meaningful when `valueState === "OK"`. */
  statusColor?: MetricStatusColor | null;
  /** Reason text selector when NOT_COMPUTABLE (10 §1.9). */
  notComputableReason?: NotComputableReason | null;
  /** Special display override (10 §1.9), e.g. `GT_24_MONTHS` → `> 24 tháng`. */
  displayHint?: MetricDisplayHint | null;
  /** Period key (`2026-09` / `2026-Q3`) → P04 `T9/2026` / `Q3/2026`. */
  periodKey: string;
  /** Signed period-over-period change as a ratio (0.082 → `+8,2%`); optional. */
  deltaRatio?: number | null;
  /** `metric_values.formula_display` — shown as the formula caption (P01). */
  formulaDisplay?: string | null;
  /** Drill-down target (→ SCR-09). The value becomes an accessible link (P01). */
  href: string;
  /** `computed_at` ISO timestamp → FreshnessLabel "Cập nhật …". */
  computedAt?: string | null;
}

/** Props for `<AlertCard>` (06 §4.1 / §6.6, AlertOut 10 §3). */
export interface AlertCardProps {
  alertCode: string;
  metricCode: string;
  pillar: Pillar;
  severity: AlertSeverity;
  /** i18n key for the alert title (`alert.<CODE>.title`); falls back to code. */
  titleI18nKey?: string;
  /** i18n key for the AI-suggested action (06 §6.3 L1). */
  suggestedActionI18nKey?: string;
  periodKey: string;
  /** ISO timestamp the alert fired (`triggered_at`). */
  triggeredAt: string;
  /** Drill-down target (→ SCR-09 filtered by the alert condition). */
  href: string;
  /** Whether the active role may acknowledge (02 §3.3); shows the acknowledge affordance. */
  canAcknowledge?: boolean;
  /** Acknowledge handler; omitted → no acknowledge button. */
  onAcknowledge?: () => void;
}

/** Props for `<TrendChart>` (06 §4.1 / §6.6; EP-12 `history[]`). */
export interface TrendChartProps {
  metricCode: string;
  /** i18n name key for the accessible chart title/summary. */
  nameI18nKey?: string;
  /** How values are formatted on axis/tooltip/summary (P04). */
  formatKind: MetricFormatKind;
  /** Time series (EP-12 `history`), oldest → newest. */
  history: MetricHistoryPoint[];
  /** Optional fixed size for deterministic jsdom tests (otherwise responsive). */
  width?: number;
  height?: number;
}

/** Props for `<AIStateBadge>` (06 §6.3). */
export interface AIStateBadgeProps {
  level: AIStateLevel;
  className?: string;
}

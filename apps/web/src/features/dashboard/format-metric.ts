/**
 * Metric value → display string, routed through the P04 `Formatter` (06 §7.1) by
 * `MetricFormatKind`. This is the single place MetricCard / TrendChart turn a raw number
 * into display text; components must not format numbers by hand (06 §7.2, CLAUDE.md).
 *
 * Unit suffixes that the shared `Formatter` does not own (days/months/tasksPerPerson/
 * vndPerPerson) are passed in from i18n `metric.unit.*` so no Vietnamese literal lives here.
 */
import type { Formatter } from "@/lib/format";
import type { MetricFormatKind } from "./types";

export interface MetricUnitLabels {
  days: string;
  months: string;
  tasksPerPerson: string;
  vndPerPerson: string;
}

/**
 * Format a finite metric value for display. Callers only reach here with an `OK` numeric
 * value — NO_DATA / NOT_COMPUTABLE never produce a fake number (they render N/A text).
 */
export function formatMetricValue(
  fmt: Formatter,
  kind: MetricFormatKind,
  value: number,
  units: MetricUnitLabels,
): string {
  switch (kind) {
    case "compactCurrency":
      return fmt.compactCurrency(value);
    case "percent":
      return fmt.percent(value);
    case "days":
      return `${fmt.number(value, 0)} ${units.days}`;
    case "months":
      return `${fmt.number(value, 1)} ${units.months}`;
    case "multiple":
      return fmt.multiple(value);
    case "count":
      return fmt.number(value, 0);
    case "score":
      return fmt.number(value, 1);
    case "tasksPerPerson":
      return `${fmt.number(value, 1)} ${units.tasksPerPerson}`;
    case "vndPerPerson":
      // Compact VND per head (e.g. `12,5 tr`) + the "/person" unit word from i18n.
      return `${fmt.compactCurrency(value)} ${units.vndPerPerson}`;
    default:
      return fmt.number(value, 1);
  }
}

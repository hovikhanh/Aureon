/** T-511 Finance drill-down (SCR-03 lite): card definitions over EP-60 + finance list endpoints. */

export type CardKey = "revenue" | "expense" | "budget" | "runway" | "cash" | "burn";
export type ValueKind = "money" | "pct" | "months";

export interface CardDef {
  key: CardKey;
  kind: ValueKind;
  /** related METRIC for status + lineage level 1 (EP-12) */
  metric: string;
  /** a rising value is good (arrow colour) */
  upIsGood: boolean;
  /** level-2 records endpoint (finance:read) */
  records: "revenues" | "expenses" | "budgets/status" | "cash-positions";
}

export const CARDS: readonly CardDef[] = [
  { key: "revenue", kind: "money", metric: "METRIC-FIN-01", upIsGood: true, records: "revenues" },
  { key: "expense", kind: "money", metric: "METRIC-FIN-02", upIsGood: false, records: "expenses" },
  { key: "budget", kind: "pct", metric: "METRIC-FIN-06", upIsGood: false, records: "budgets/status" },
  { key: "runway", kind: "months", metric: "METRIC-FIN-03", upIsGood: true, records: "cash-positions" },
  { key: "cash", kind: "money", metric: "METRIC-FIN-03", upIsGood: true, records: "cash-positions" },
  { key: "burn", kind: "money", metric: "METRIC-FIN-07", upIsGood: false, records: "expenses" },
];

export type Trend = "up" | "down" | "flat" | null;

/** Direction of the last step of a series (display only — values come from the API). */
export function trendOf(series: readonly number[]): Trend {
  if (series.length < 2) return null;
  const a = series[series.length - 2] as number;
  const b = series[series.length - 1] as number;
  if (b === a) return "flat";
  return b > a ? "up" : "down";
}

/** Month key used by month-only list endpoints: the month itself or the last month of a quarter. */
export function monthOf(period: { key: string; end_date: string }): string {
  return /^\d{4}-\d{2}$/.test(period.key) ? period.key : period.end_date.slice(0, 7);
}

/** IDP-committed invoices carry `Committed from IDP document <uuid>` in notes (ACT-commit). */
export function idpDocumentId(notes: string | null | undefined): string | null {
  const m = /IDP document ([0-9a-f-]{36})/i.exec(notes ?? "");
  return m?.[1] ?? null;
}

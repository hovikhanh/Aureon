/**
 * P04 formatting helpers — docs/2.PRODUCT/06-UI-UX-SPEC.md §7.1, §7.2 (TC-UI-001).
 * The single shared place for number/date/money formatting; components must not format
 * values themselves. Unit words (currency suffix, million/billion, period prefixes,
 * placeholder) are i18n messages (`format.*` in messages/*.json) passed in as `labels`,
 * so no Vietnamese literal lives in src/ (TC-UI-005).
 *
 * Input conventions follow 10 §1.1: money = integer VND, ratios = decimals
 * (0.125 = 12,5%), timestamps = ISO 8601 with offset, plain dates = `YYYY-MM-DD`,
 * periods = `YYYY-MM` / `YYYY-Qn` (05 C9).
 */
import { INTL_LOCALE, TIME_ZONE, type AppLocale } from "@/i18n/config";

export interface FormatLabels {
  /** Suffix for full money amounts, e.g. `1.250.000 đ`. */
  currencySuffix: string;
  /** Compact unit for 10^6, e.g. `850 tr`. */
  million: string;
  /** Compact unit for 10^9, e.g. `1,2 tỷ`. */
  billion: string;
  /** Month period prefix, e.g. `T9/2026`. */
  monthPrefix: string;
  /** Quarter period prefix, e.g. `Q3/2026`. */
  quarterPrefix: string;
  /** Shown for missing/non-computable values (06 §4.1 empty card: `—`). */
  placeholder: string;
}

export type Numeric = number | null | undefined;
export type DateInput = string | Date | null | undefined;

const MILLION = 1_000_000;
const BILLION = 1_000_000_000;
const PLAIN_DATE = /^(\d{4})-(\d{2})-(\d{2})$/;
const MONTH_PERIOD = /^(\d{4})-(0[1-9]|1[0-2])$/;
const QUARTER_PERIOD = /^(\d{4})-Q([1-4])$/;

function isFiniteNumber(value: Numeric): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function toDate(input: DateInput): { date: Date; timeZone: string } | null {
  if (input === null || input === undefined) return null;
  if (input instanceof Date) {
    return Number.isNaN(input.getTime()) ? null : { date: input, timeZone: TIME_ZONE };
  }
  const plain = PLAIN_DATE.exec(input);
  if (plain) {
    // Calendar date without time: format in UTC so it never shifts a day.
    const [, y, m, d] = plain;
    const date = new Date(Date.UTC(Number(y), Number(m) - 1, Number(d)));
    const valid =
      date.getUTCFullYear() === Number(y) &&
      date.getUTCMonth() === Number(m) - 1 &&
      date.getUTCDate() === Number(d);
    return valid ? { date, timeZone: "UTC" } : null;
  }
  const date = new Date(input);
  return Number.isNaN(date.getTime()) ? null : { date, timeZone: TIME_ZONE };
}

/** Format, mapping a negative value that rounds to zero ("-0", "-0,0%") to unsigned zero. */
function formatNoNegativeZero(fmt: Intl.NumberFormat, value: number): string {
  const out = fmt.format(value);
  return value < 0 && !/[1-9]/.test(out) ? fmt.format(0) : out;
}

export interface Formatter {
  /** `1.250.000 đ` — full money (tables, forms, Review). Rounded to whole VND. */
  currency(value: Numeric): string;
  /** `850 tr`, `1,2 tỷ` — compact money (MetricCard, chart axes). < 1 million → full currency. */
  compactCurrency(value: Numeric): string;
  /** `12,5%` from ratio `0.125` — always 1 decimal. */
  percent(value: Numeric): string;
  /** `+8,2%` / `-3,4%` / `0,0%` — signed change from a ratio. */
  percentChange(value: Numeric): string;
  /** `5,4` — plain number, dot grouping, comma decimal (max `fractionDigits`, default 1). */
  number(value: Numeric, fractionDigits?: number): string;
  /** `2,8x` — multiple. */
  multiple(value: Numeric): string;
  /** `05/10/2026`. */
  date(value: DateInput): string;
  /** `05/10/2026 08:30` (24h, Asia/Ho_Chi_Minh). */
  dateTime(value: DateInput): string;
  /** `T9/2026` from `2026-09`, `Q3/2026` from `2026-Q3`. */
  period(periodKey: string | null | undefined): string;
}

export function createFormatter(labels: FormatLabels, locale: AppLocale = "vi"): Formatter {
  const tag = INTL_LOCALE[locale];
  const decimalFormats = new Map<number, Intl.NumberFormat>();
  const decimalFormat = (maxFractionDigits: number, minFractionDigits = 0) => {
    const key = maxFractionDigits * 10 + minFractionDigits;
    let fmt = decimalFormats.get(key);
    if (!fmt) {
      fmt = new Intl.NumberFormat(tag, {
        minimumFractionDigits: minFractionDigits,
        maximumFractionDigits: maxFractionDigits,
      });
      decimalFormats.set(key, fmt);
    }
    return fmt;
  };
  const decimal = (maxFractionDigits: number, minFractionDigits = 0) => ({
    format: (value: number) =>
      formatNoNegativeZero(decimalFormat(maxFractionDigits, minFractionDigits), value),
  });
  const percentFmt = new Intl.NumberFormat(tag, {
    style: "percent",
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  });
  const percentChangeFmt = new Intl.NumberFormat(tag, {
    style: "percent",
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
    // exceptZero also renders a negative value rounding to zero as "0,0%".
    signDisplay: "exceptZero",
  });

  const dateParts = (value: DateInput, withTime: boolean) => {
    const parsed = toDate(value);
    if (!parsed) return null;
    const parts = new Intl.DateTimeFormat("en-GB", {
      timeZone: withTime ? TIME_ZONE : parsed.timeZone,
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      ...(withTime ? { hour: "2-digit", minute: "2-digit", hourCycle: "h23" as const } : {}),
    }).formatToParts(parsed.date);
    const get = (type: Intl.DateTimeFormatPartTypes) =>
      parts.find((p) => p.type === type)?.value ?? "";
    return { day: get("day"), month: get("month"), year: get("year"), hour: get("hour"), minute: get("minute") };
  };

  const formatter: Formatter = {
    currency(value) {
      if (!isFiniteNumber(value)) return labels.placeholder;
      return `${decimal(0).format(Math.round(value) || 0)} ${labels.currencySuffix}`;
    },
    compactCurrency(value) {
      if (!isFiniteNumber(value)) return labels.placeholder;
      const abs = Math.abs(value);
      if (abs < MILLION) return formatter.currency(value);
      const sign = value < 0 ? -1 : 1;
      // Round to 1 decimal first so 999,96 tr is promoted to 1 tỷ (not "1.000 tr").
      const millions = Math.round((abs / MILLION) * 10) / 10;
      if (millions < 1000) return `${decimal(1).format(sign * millions)} ${labels.million}`;
      const billions = Math.round((abs / BILLION) * 10) / 10;
      return `${decimal(1).format(sign * billions)} ${labels.billion}`;
    },
    percent(value) {
      return isFiniteNumber(value) ? formatNoNegativeZero(percentFmt, value) : labels.placeholder;
    },
    percentChange(value) {
      return isFiniteNumber(value) ? percentChangeFmt.format(value) : labels.placeholder;
    },
    number(value, fractionDigits = 1) {
      return isFiniteNumber(value) ? decimal(fractionDigits).format(value) : labels.placeholder;
    },
    multiple(value) {
      return isFiniteNumber(value) ? `${decimal(1).format(value)}x` : labels.placeholder;
    },
    date(value) {
      const p = dateParts(value, false);
      return p ? `${p.day}/${p.month}/${p.year}` : labels.placeholder;
    },
    dateTime(value) {
      // A plain `YYYY-MM-DD` has no time component; show it as a date only.
      if (typeof value === "string" && PLAIN_DATE.test(value)) return formatter.date(value);
      const p = dateParts(value, true);
      return p ? `${p.day}/${p.month}/${p.year} ${p.hour}:${p.minute}` : labels.placeholder;
    },
    period(periodKey) {
      if (!periodKey) return labels.placeholder;
      const month = MONTH_PERIOD.exec(periodKey);
      if (month) return `${labels.monthPrefix}${Number(month[2])}/${month[1]}`;
      const quarter = QUARTER_PERIOD.exec(periodKey);
      if (quarter) return `${labels.quarterPrefix}${quarter[2]}/${quarter[1]}`;
      return labels.placeholder;
    },
  };
  return formatter;
}

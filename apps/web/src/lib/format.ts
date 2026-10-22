/** P04 / 06 §8.1 — the single formatting helper (no ad-hoc formatting in components). */
export type AppLocale = "vi" | "en";

const tag = (l: AppLocale) => (l === "vi" ? "vi-VN" : "en-US");

export function formatNumber(value: number, locale: AppLocale, digits = 1): string {
  return new Intl.NumberFormat(tag(locale), { maximumFractionDigits: digits }).format(value);
}

export function formatPct(value: number, locale: AppLocale): string {
  return `${new Intl.NumberFormat(tag(locale), { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(value)}%`;
}

/** Full money: `1.250.000 đ` / `VND 1,250,000`. Amounts are BIGINT VND units. */
export function formatMoney(value: number, locale: AppLocale): string {
  const n = new Intl.NumberFormat(tag(locale), { maximumFractionDigits: 0 }).format(value);
  return locale === "vi" ? `${n} đ` : `VND ${n}`;
}

/** Short money: `850 tr`, `1,2 tỷ` / `VND 850M`, `VND 1.2B`. */
export function formatMoneyShort(value: number, locale: AppLocale): string {
  const abs = Math.abs(value);
  const f = (x: number) => formatNumber(x, locale, 1);
  if (abs >= 1e9) return locale === "vi" ? `${f(value / 1e9)} tỷ` : `VND ${f(value / 1e9)}B`;
  if (abs >= 1e6) return locale === "vi" ? `${f(value / 1e6)} tr` : `VND ${f(value / 1e6)}M`;
  return formatMoney(value, locale);
}

export function formatDate(iso: string, locale: AppLocale): string {
  const d = new Date(iso);
  return locale === "vi"
    ? new Intl.DateTimeFormat("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric", timeZone: "Asia/Ho_Chi_Minh" }).format(d)
    : new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric", timeZone: "Asia/Ho_Chi_Minh" }).format(d);
}

export function formatDateTime(iso: string, locale: AppLocale): string {
  const d = new Date(iso);
  return new Intl.DateTimeFormat(tag(locale), {
    day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit",
    hour12: false, timeZone: "Asia/Ho_Chi_Minh",
  }).format(d);
}

/** `T9/2026` / `Sep 2026`; quarters `Q3/2026` / `Q3 2026`. */
export function formatPeriod(key: string, locale: AppLocale): string {
  const m = /^(\d{4})-(\d{2})$/.exec(key);
  if (m) {
    const [, y, mo] = m;
    if (locale === "vi") return `T${Number(mo)}/${y}`;
    return new Intl.DateTimeFormat("en-US", { month: "short", year: "numeric", timeZone: "UTC" }).format(
      new Date(Date.UTC(Number(y), Number(mo) - 1, 1)),
    );
  }
  const q = /^(\d{4})-Q(\d)$/.exec(key);
  if (q) return locale === "vi" ? `Q${q[2]}/${q[1]}` : `Q${q[2]} ${q[1]}`;
  return key;
}

/** Metric value by unit (API returns code + value; FE only formats, never computes KPIs). */
export function formatMetric(value: number | null, unit: string, locale: AppLocale, unitLabel = ""): string {
  if (value === null || Number.isNaN(value)) return "—";
  switch (unit) {
    case "PCT":
      return formatPct(value, locale);
    case "VND":
      return formatMoneyShort(value, locale);
    case "RATIO":
      return `${formatNumber(value, locale, 1)}x`;
    default:
      return unitLabel ? `${formatNumber(value, locale, 1)} ${unitLabel}` : formatNumber(value, locale, 1);
  }
}

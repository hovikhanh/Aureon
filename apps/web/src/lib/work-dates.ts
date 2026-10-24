/**
 * Business-date helpers for D11 Work (10 §7.2.2): `due_date` is compared with the business day in
 * `Asia/Ho_Chi_Minh` (`business_today()` BE-side); workload weeks are ISO weeks `YYYY-Www`
 * (EP-TASK-18). Pure functions on `YYYY-MM-DD` strings (no local-timezone drift).
 */
export const BUSINESS_TZ = "Asia/Ho_Chi_Minh";

/** Business today `YYYY-MM-DD`: `DEMO_REFERENCE_DATE` in demo (same as the API `business_today()`), else the Asia/Ho_Chi_Minh date. */
export function businessToday(now: Date = new Date(), ref: string | undefined = process.env.NEXT_PUBLIC_DEMO_REFERENCE_DATE): string {
  if (ref && /^\d{4}-\d{2}-\d{2}$/.test(ref)) return ref;
  return new Intl.DateTimeFormat("en-CA", { timeZone: BUSINESS_TZ, year: "numeric", month: "2-digit", day: "2-digit" }).format(now);
}

const toUtc = (iso: string) => new Date(`${iso}T00:00:00Z`);
const fromUtc = (d: Date) => d.toISOString().slice(0, 10);

export function addDays(iso: string, days: number): string {
  const d = toUtc(iso);
  d.setUTCDate(d.getUTCDate() + days);
  return fromUtc(d);
}

export function isIsoDate(v: string | null | undefined): v is string {
  return Boolean(v && /^\d{4}-\d{2}-\d{2}$/.test(v) && !Number.isNaN(Date.parse(v)) && fromUtc(toUtc(v)) === v);
}

/** ISO weekday 1 (Mon) … 7 (Sun). */
const isoDow = (iso: string) => ((toUtc(iso).getUTCDay() + 6) % 7) + 1;

/** Monday of the week containing `iso`. */
export function weekStart(iso: string): string {
  return addDays(iso, 1 - isoDow(iso));
}

/** ISO week label `YYYY-Www` of a date. */
export function isoWeek(iso: string): string {
  const thursday = addDays(iso, 4 - isoDow(iso));
  const year = Number(thursday.slice(0, 4));
  const jan4 = `${year}-01-04`;
  const week = 1 + Math.round((toUtc(weekStart(thursday)).getTime() - toUtc(weekStart(jan4)).getTime()) / (7 * 86_400_000));
  return `${year}-W${String(week).padStart(2, "0")}`;
}

export function isIsoWeek(v: string | null | undefined): v is string {
  const m = v ? /^(\d{4})-W(\d{2})$/.exec(v) : null;
  if (!m) return false;
  const w = Number(m[2]);
  return w >= 1 && w <= 53 && isoWeek(weekRange(v as string).start) === v;
}

/** Monday..Sunday of an ISO week label (no validation — use `isIsoWeek`). */
export function weekRange(week: string): { start: string; end: string } {
  const [y, w] = [Number(week.slice(0, 4)), Number(week.slice(6))];
  const start = addDays(weekStart(`${y}-01-04`), (w - 1) * 7);
  return { start, end: addDays(start, 6) };
}

/** `count` consecutive ISO weeks ending with `last` (oldest first). */
export function weeksEnding(last: string, count: number): string[] {
  const { start } = weekRange(last);
  return Array.from({ length: count }, (_, i) => isoWeek(addDays(start, -7 * (count - 1 - i))));
}

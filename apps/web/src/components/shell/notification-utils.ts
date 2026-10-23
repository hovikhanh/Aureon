/** Pure helpers of the Header bell (T-617F, 06 §3.4) — unit-tested. */

/** Badge text: hidden at 0, the number up to 99, then "99+". */
export function badgeText(unread: number): string | null {
  if (!Number.isFinite(unread) || unread <= 0) return null;
  return unread > 99 ? "99+" : String(Math.floor(unread));
}

/** Only relative in-app paths are followed (no `//host`, no scheme) — same rule as the email link. */
export function safeInAppLink(link: string | null | undefined): string | null {
  if (!link || !link.startsWith("/") || link.startsWith("//") || link.includes("\\")) return null;
  return link;
}

const STEPS: [Intl.RelativeTimeFormatUnit, number][] = [["second", 60], ["minute", 60], ["hour", 24], ["day", 30], ["month", 12], ["year", Infinity]];

/** "3 phút trước" / "3 minutes ago". */
export function relativeTime(iso: string, locale: string, now: number = Date.now()): string {
  let value = (Date.parse(iso) - now) / 1000;
  const fmt = new Intl.RelativeTimeFormat(locale === "en" ? "en" : "vi", { numeric: "auto" });
  for (const [unit, size] of STEPS) {
    if (Math.abs(value) < size) return fmt.format(Math.round(value), unit);
    value /= size;
  }
  return fmt.format(Math.round(value), "year");
}

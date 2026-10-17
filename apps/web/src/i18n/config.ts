/**
 * i18n configuration — next-intl (DEC-064), non-routing setup.
 * 06 §7.2: `vi` is the default (and currently only active) locale; keys are structured so
 * `en` can be enabled later. 06 §2.3 routes carry no locale segment, hence no [locale] routing.
 */
export const LOCALES = ["vi", "en"] as const;
export type AppLocale = (typeof LOCALES)[number];
export const DEFAULT_LOCALE: AppLocale = "vi";

/** BCP 47 tag used for Intl formatting (06 U8: `vi-VN`). */
export const INTL_LOCALE: Record<AppLocale, string> = {
  vi: "vi-VN",
  en: "en-US",
};

/** Business time zone for date formatting (10 §1.1 timestamps are `+07:00`). */
export const TIME_ZONE = "Asia/Ho_Chi_Minh";

export function isAppLocale(value: unknown): value is AppLocale {
  return typeof value === "string" && (LOCALES as readonly string[]).includes(value);
}

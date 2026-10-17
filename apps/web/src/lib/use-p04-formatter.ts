import { useLocale, useTranslations } from "next-intl";
import { useMemo } from "react";
import { isAppLocale, DEFAULT_LOCALE } from "@/i18n/config";
import { createFormatter, type Formatter } from "./format";

/**
 * P04 formatter (named to avoid clashing with next-intl `useFormatter`) bound to the active locale and its `format.*` message labels.
 * Works in Server Components (non-async) and Client Components under NextIntlClientProvider.
 */
export function useP04Formatter(): Formatter {
  const t = useTranslations("format");
  const rawLocale = useLocale();
  const locale = isAppLocale(rawLocale) ? rawLocale : DEFAULT_LOCALE;
  return useMemo(
    () =>
      createFormatter(
        {
          currencySuffix: t("currencySuffix"),
          million: t("million"),
          billion: t("billion"),
          monthPrefix: t("monthPrefix"),
          quarterPrefix: t("quarterPrefix"),
          placeholder: t("placeholder"),
        },
        locale,
      ),
    [t, locale],
  );
}

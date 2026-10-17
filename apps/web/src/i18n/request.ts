import { getRequestConfig } from "next-intl/server";
import { DEFAULT_LOCALE, TIME_ZONE } from "./config";

/**
 * next-intl request config (non-routing). The MVP serves `vi` only (06 §7.2); locale
 * switching (cookie/user profile) is out of scope until a later task asks for `en`.
 */
export default getRequestConfig(async () => {
  const locale = DEFAULT_LOCALE;
  const messages = (await import(`../../messages/${locale}.json`)).default;
  return { locale, messages, timeZone: TIME_ZONE };
});

import { useTranslations } from "next-intl";
import type { MaskedMetricValue } from "@/features/dashboard/types";
import { cn } from "@/lib/utils";

/**
 * MaskedValue — renders `••••` for a salary field the active role may not see (06 §7.4,
 * 10 §1.8 DS3). The API never sends a real value for a masked field: it sends only
 * `{ masked: true }`, so there is no real value in the DOM to leak. The visible dots carry
 * an accessible label ("Lương được ẩn" via i18n `metric.masked.label`) and a `title` tooltip
 * explaining who may see it. The dot count is fixed and does NOT reflect the real digit count
 * (06 §7.4). It only ever accepts `{ masked: true }` — never a number.
 */
export function MaskedValue({
  value,
  className,
}: {
  /** Must be `{ masked: true }` (10 §1.8 DS3). The shape guarantees no real value is passed. */
  value: MaskedMetricValue;
  className?: string;
}) {
  const t = useTranslations("metric.masked");
  // `value.masked` is always true by type; referencing it keeps the contract explicit.
  void value.masked;
  const label = t("label");
  return (
    <span
      data-masked="true"
      role="img"
      aria-label={label}
      title={t("tooltip")}
      className={cn("inline-flex items-center font-data tracking-widest text-neutral-500", className)}
    >
      <span aria-hidden="true">{t("dots")}</span>
    </span>
  );
}

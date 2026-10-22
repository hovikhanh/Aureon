"use client";
import { useLocale, useTranslations } from "next-intl";
import { CalendarDays } from "lucide-react";
import { NativeSelect } from "@/components/ui/select";
import { formatPeriod, type AppLocale } from "@/lib/format";
import { PERIOD_CHOICES, choiceOf, periodFor, usePeriod } from "./period";

/** T-510: "Kỳ báo cáo: T9/2026" label + picker [Tháng này | Tháng trước | Q3 | Q4]. */
export function PeriodPicker() {
  const t = useTranslations("dashboard.period");
  const locale = useLocale() as AppLocale;
  const { period, setPeriod } = usePeriod();
  const current = choiceOf(period);
  return (
    <div className="flex flex-wrap items-center gap-2 text-sm" data-testid="period-picker">
      <CalendarDays className="h-4 w-4 text-muted-foreground" aria-hidden />
      <span className="text-muted-foreground" data-testid="period-label" data-period={period}>
        {t("label", { period: formatPeriod(period, locale) })}
      </span>
      <label className="sr-only" htmlFor="period-select">{t("choose")}</label>
      <NativeSelect
        id="period-select"
        className="h-8 w-auto min-w-40"
        value={current ?? ""}
        onChange={(e) => setPeriod(periodFor(e.target.value as (typeof PERIOD_CHOICES)[number]))}
        data-testid="period-select"
      >
        {!current && <option value="">{formatPeriod(period, locale)}</option>}
        {PERIOD_CHOICES.map((c) => (
          <option key={c} value={c}>
            {t(`choice.${c}`, { period: formatPeriod(periodFor(c), locale) })}
          </option>
        ))}
      </NativeSelect>
    </div>
  );
}

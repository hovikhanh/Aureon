"use client";
import { useLocale, useTranslations } from "next-intl";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { formatNumber, formatPeriod, type AppLocale } from "@/lib/format";
import type { SourceRef } from "@/features/ai/types";

/** 06 §5.1 SourceChip — citation `[n]` opening a popover with the source (P01, P05). */
export function SourceChip({ n, source }: { n: number; source?: SourceRef }) {
  const t = useTranslations("ai");
  const locale = useLocale() as AppLocale;
  if (!source) return <sup className="text-muted-foreground">[{n}]</sup>;
  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          data-testid="citation"
          className="mx-0.5 inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-ai-subtle px-1.5 align-super text-[10px] font-semibold text-ai hover:bg-ai hover:text-ai-foreground"
          aria-label={`${t("sources")} ${n}: ${source.label}`}
        >
          {n}
        </button>
      </PopoverTrigger>
      <PopoverContent data-testid="source-popover">
        <div className="mb-2 font-semibold">{source.label}</div>
        <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs">
          <dt className="text-muted-foreground">{t("sourceType")}</dt>
          <dd>{source.type}</dd>
          <dt className="text-muted-foreground">ID</dt>
          <dd className="break-all font-mono">{source.id}</dd>
          {source.period_key && (<><dt className="text-muted-foreground">{t("sourcePeriod")}</dt><dd>{formatPeriod(source.period_key, locale)}</dd></>)}
          {typeof source.value === "number" && (<><dt className="text-muted-foreground">{t("sourceValue")}</dt><dd className="tabular-nums">{formatNumber(source.value, locale, 2)}</dd></>)}
        </dl>
        {source.lineage_url && <p className="mt-2 break-all text-xs text-ai">{t("openLineage")}: {source.lineage_url}</p>}
      </PopoverContent>
    </Popover>
  );
}

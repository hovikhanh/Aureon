"use client";
import { useLocale, useTranslations } from "next-intl";
import { Badge } from "@/components/ui/badge";
import { formatPct, type AppLocale } from "@/lib/format";
import type { ConfidenceBand } from "@/features/idp/types";

const VARIANT = { HIGH: "success", MEDIUM: "warning", LOW: "danger" } as const;
const ICON = { HIGH: "●", MEDIUM: "◐", LOW: "○" } as const;

/** 06 §5.1 ConfidenceBadge — DEC-133 bands (Cao ≥0,90 · TB 0,60–<0,90 · Thấp <0,60). */
export function bandOf(c: number | null): ConfidenceBand | null {
  if (c === null) return null;
  return c >= 0.9 ? "HIGH" : c >= 0.6 ? "MEDIUM" : "LOW";
}

export function ConfidenceBadge({ value, band }: { value: number | null; band?: ConfidenceBand | null }) {
  const t = useTranslations("idp.confidence");
  const locale = useLocale() as AppLocale;
  const b = band ?? bandOf(value);
  if (!b) return <Badge>—</Badge>;
  return (
    <Badge variant={VARIANT[b]} data-testid="confidence-badge" data-band={b}>
      <span aria-hidden>{ICON[b]}</span>
      {t(b)}
      {value !== null && <span className="tabular-nums">· {formatPct(value * 100, locale)}</span>}
    </Badge>
  );
}

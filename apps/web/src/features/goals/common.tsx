"use client";
/** Shared bits of the goals screens: error text, inline load error, band chip, confidence badge, progress bar, at-risk flag. */
import * as React from "react";
import { useTranslations } from "next-intl";
import { ApiError } from "@/lib/api-client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { BAND_VARIANT, goalErrorKey, type Band, type Confidence } from "./logic";

export function useGoalError(): (e: unknown) => string {
  const t = useTranslations("goals.errors");
  return React.useCallback((e: unknown) => (e instanceof ApiError ? t(goalErrorKey(e) as "generic") : t("generic")), [t]);
}

export function LoadError({ onRetry, testId }: { onRetry: () => void; testId?: string }) {
  const t = useTranslations("goals");
  return (
    <div role="alert" className="flex items-center gap-3 rounded border border-danger/40 bg-danger-subtle p-3 text-sm text-danger" data-testid={testId ?? "goals-load-error"}>
      {t("loadError")}
      <Button size="sm" variant="outline" onClick={onRetry}>{t("retry")}</Button>
    </div>
  );
}

export function BandChip({ band }: { band: Band | null | undefined }) {
  const t = useTranslations("goals");
  if (!band) return <Badge data-testid="band-chip" data-band="none">{t("tree.noEvaluation")}</Badge>;
  return <Badge variant={BAND_VARIANT[band]} data-testid="band-chip" data-band={band}>{t(`band.${band}`)}</Badge>;
}

const CONF_VARIANT = { HIGH: "success", MEDIUM: "warning", LOW: "danger" } as const;
const CONF_ICON = { HIGH: "●", MEDIUM: "◐", LOW: "○" } as const;
/** 06 §5.1 ConfidenceBadge for the 3-step KR confidence (no numeric value — 05 §2.6). */
export function KrConfidence({ value }: { value: Confidence | string | null | undefined }) {
  const t = useTranslations("goals.confidence");
  if (value !== "HIGH" && value !== "MEDIUM" && value !== "LOW") return <Badge data-testid="confidence-badge" data-band="none">{t("none")}</Badge>;
  return (
    <Badge variant={CONF_VARIANT[value]} data-testid="confidence-badge" data-band={value} aria-label={`${t("label")}: ${t(value)}`}>
      <span aria-hidden>{CONF_ICON[value]}</span>{t(value)}
    </Badge>
  );
}

export function AtRiskFlag() {
  const t = useTranslations("goals.atRisk");
  return <Badge variant="danger" data-testid="at-risk-flag">⚠ {t("flag")}</Badge>;
}

export function Progress({ value, label }: { value: number; label: string }) {
  const pct = Math.max(0, Math.min(100, value));
  return (
    <div className="h-1.5 w-24 overflow-hidden rounded-full bg-muted" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(pct)} aria-label={label}>
      <div className="h-full bg-primary" style={{ width: `${pct}%` }} />
    </div>
  );
}

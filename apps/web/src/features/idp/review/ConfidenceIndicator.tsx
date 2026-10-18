"use client";

import { useTranslations } from "next-intl";
import { CheckCircle2, AlertCircle, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";

export interface ConfidenceIndicatorProps {
  confidence: number | null | undefined;
  band?: "HIGH" | "MEDIUM" | "LOW";
  className?: string;
  showPercent?: boolean;
}

export function ConfidenceIndicator({
  confidence,
  band,
  className,
  showPercent = true,
}: ConfidenceIndicatorProps) {
  const t = useTranslations("review");

  let computedBand: "HIGH" | "MEDIUM" | "LOW" = "LOW";
  if (band) {
    computedBand = band;
  } else if (confidence !== null && confidence !== undefined) {
    if (confidence >= 0.90) {
      computedBand = "HIGH";
    } else if (confidence >= 0.70) {
      computedBand = "MEDIUM";
    } else {
      computedBand = "LOW";
    }
  }

  const percentScore =
    confidence !== null && confidence !== undefined
      ? Math.round(confidence * 100)
      : null;

  return (
    <div
      role="status"
      data-testid="confidence-indicator"
      data-confidence-band={computedBand}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium border select-none",
        computedBand === "HIGH" &&
          "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800",
        computedBand === "MEDIUM" &&
          "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800",
        computedBand === "LOW" &&
          "bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-950/40 dark:text-rose-300 dark:border-rose-800",
        className,
      )}
      title={percentScore !== null ? t("confidenceScore", { score: percentScore }) : undefined}
    >
      {computedBand === "HIGH" && (
        <CheckCircle2 className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
      )}
      {computedBand === "MEDIUM" && (
        <AlertCircle className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
      )}
      {computedBand === "LOW" && (
        <AlertTriangle className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
      )}

      <span>
        {computedBand === "HIGH" && t("confidenceHigh")}
        {computedBand === "MEDIUM" && t("confidenceMedium")}
        {computedBand === "LOW" && t("confidenceLow")}
      </span>

      {showPercent && percentScore !== null && (
        <span className="tabular-nums opacity-85">({percentScore}%)</span>
      )}
    </div>
  );
}

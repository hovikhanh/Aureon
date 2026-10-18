"use client";

import { useTranslations } from "next-intl";
import { Check, RotateCcw, Target } from "lucide-react";
import type { ExtractedFieldOut } from "@aureon/shared-types";
import { MaskedValue } from "@/components/metric/MaskedValue";
import { cn } from "@/lib/utils";
import { ConfidenceIndicator } from "./ConfidenceIndicator";
import type { FieldEditState } from "./types";

export interface ExtractionFieldRowProps {
  field: ExtractedFieldOut;
  editState: FieldEditState;
  isSelected?: boolean;
  onSelect?: () => void;
  onChangeValue?: (newValue: unknown) => void;
  onConfirm?: () => void;
  onRevert?: () => void;
  className?: string;
}

function formatDisplayValue(val: unknown): string {
  if (val === null || val === undefined) return "";
  if (typeof val === "object") return JSON.stringify(val);
  return String(val);
}

export function ExtractionFieldRow({
  field,
  editState,
  isSelected = false,
  onSelect,
  onChangeValue,
  onConfirm,
  onRevert,
  className,
}: ExtractionFieldRowProps) {
  const t = useTranslations("review");

  const isLowOrMedium =
    field.confidence_band === "LOW" || field.confidence_band === "MEDIUM";
  const needsConfirmation = isLowOrMedium && !editState.isConfirmed && !editState.isCorrected;

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!onChangeValue) return;
    const raw = e.target.value;
    if (field.value_type === "NUMBER" || field.value_type === "CURRENCY") {
      const num = Number(raw.replace(/[^0-9.-]+/g, ""));
      onChangeValue(isNaN(num) ? raw : num);
    } else {
      onChangeValue(raw);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && onConfirm) {
      e.preventDefault();
      onConfirm();
    }
  };

  return (
    <div
      data-testid={`field-row-${field.field_key}`}
      data-field-key={field.field_key}
      className={cn(
        "flex flex-col gap-2 rounded-lg border p-3 transition-colors",
        isSelected
          ? "border-primary bg-primary/5 ring-1 ring-primary"
          : needsConfirmation
          ? field.confidence_band === "LOW"
            ? "border-rose-300 bg-rose-50/20 dark:border-rose-900/60 dark:bg-rose-950/10"
            : "border-amber-300 bg-amber-50/20 dark:border-amber-900/60 dark:bg-amber-950/10"
          : "border-border bg-card",
        className,
      )}
    >
      {/* Top line: Label, Required, Tags, Confidence */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-1.5">
          <label
            htmlFor={`field-input-${field.id}`}
            className="text-xs font-semibold text-foreground cursor-pointer select-none"
          >
            {field.field_key}
          </label>
          {field.required && (
            <span
              className="text-rose-500 font-bold select-none"
              title={t("fieldRequired")}
              aria-label={t("fieldRequired")}
            >
              *
            </span>
          )}

          {editState.isCorrected && (
            <span className="rounded bg-blue-100 px-1.5 py-0.5 text-[10px] font-medium text-blue-700 dark:bg-blue-900/40 dark:text-blue-300">
              {t("fieldCorrected")}
            </span>
          )}
          {editState.isConfirmed && !editState.isCorrected && (
            <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-[10px] font-medium text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300">
              {t("fieldConfirmed")}
            </span>
          )}
        </div>

        <ConfidenceIndicator
          confidence={field.confidence}
          band={field.confidence_band}
        />
      </div>

      {/* Input line */}
      <div className="flex items-center gap-2">
        {field.masked ? (
          <div className="flex h-9 w-full items-center rounded-md border border-input bg-muted px-3 text-sm">
            <MaskedValue value={{ masked: true }} />
          </div>
        ) : (
          <input
            id={`field-input-${field.id}`}
            type="text"
            value={formatDisplayValue(editState.currentValue)}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            onFocus={onSelect}
            placeholder={t("editPlaceholder")}
            className={cn(
              "flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm text-foreground shadow-xs transition-colors",
              "focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary",
              needsConfirmation && "border-amber-400 dark:border-amber-600",
            )}
          />
        )}

        {/* Locate in document button */}
        {field.source_location && onSelect && (
          <button
            type="button"
            onClick={onSelect}
            className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-border bg-background text-muted-foreground hover:bg-muted hover:text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            title={t("highlightInDoc")}
            aria-label={`${t("highlightInDoc")} ${field.field_key}`}
          >
            <Target className="h-4 w-4" aria-hidden="true" />
          </button>
        )}

        {/* Confirm button for yellow/red fields */}
        {needsConfirmation && onConfirm && (
          <button
            type="button"
            onClick={onConfirm}
            className="inline-flex h-9 items-center gap-1 shrink-0 rounded-md bg-secondary px-2.5 text-xs font-medium text-secondary-foreground hover:bg-secondary/80 focus:outline-none focus:ring-2 focus:ring-primary"
            aria-label={`${t("confirmButton")} ${field.field_key}`}
          >
            <Check className="h-3.5 w-3.5" aria-hidden="true" />
            <span>{t("confirmButton")}</span>
          </button>
        )}

        {/* Revert button if corrected */}
        {editState.isCorrected && onRevert && (
          <button
            type="button"
            onClick={onRevert}
            className="inline-flex h-9 items-center gap-1 shrink-0 rounded-md border border-border bg-background px-2 text-xs font-medium text-muted-foreground hover:bg-muted hover:text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            title={t("revertButton")}
            aria-label={`${t("revertButton")} ${field.field_key}`}
          >
            <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
          </button>
        )}
      </div>
    </div>
  );
}

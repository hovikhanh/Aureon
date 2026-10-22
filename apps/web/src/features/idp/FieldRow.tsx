"use client";
import { useTranslations } from "next-intl";
import { AlertCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { ConfidenceBadge } from "@/components/ConfidenceBadge";
import { cn } from "@/lib/utils";
import type { ReviewField } from "./types";

export interface FieldDraft {
  confirmed: boolean;
  value: string;
  reason: string;
}

export const MONEY_TYPES = new Set(["money"]);
export const display = (v: unknown) => (v === null || v === undefined ? "" : String(v));

interface Props {
  field: ReviewField;
  label: string;
  draft: FieldDraft;
  error?: string;
  active: boolean;
  disabled: boolean;
  onFocus: () => void;
  onChange: (d: FieldDraft) => void;
}

export function FieldRow({ field, label, draft, error, active, disabled, onFocus, onChange }: Props) {
  const t = useTranslations("idp");
  const failing = field.validation.filter((v) => v.status === "fail");
  const corrected = draft.value !== display(field.effective_value);
  const invalid = Boolean(error) || failing.length > 0;
  const tip = error ?? failing.map((v) => v.message).join("; ");
  return (
    <div
      data-testid="field-row"
      data-field={field.field_name}
      onFocusCapture={onFocus}
      onMouseEnter={onFocus}
      className={cn("grid gap-2 rounded-lg border p-3 transition-colors", active && "border-primary bg-primary/5", invalid && "border-danger")}
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-medium">{label}</span>
        {field.is_critical && <Badge variant="danger">{t("field.critical")}</Badge>}
        <ConfidenceBadge value={field.confidence} band={field.confidence_band} />
        {corrected && <Badge variant="primary">{t("field.corrected")}</Badge>}
        <label className="ml-auto flex items-center gap-2 text-sm">
          <Checkbox checked={draft.confirmed} disabled={disabled} onCheckedChange={(c) => onChange({ ...draft, confirmed: c === true })} aria-label={`${t("field.confirm")} ${label}`} data-testid="field-confirm" />
          {t("field.confirm")}
        </label>
      </div>
      <div className="text-xs text-muted-foreground">{t("field.value")}: <span className="font-mono text-foreground">{display(field.ai_value) || "—"}</span></div>
      <div className="relative">
        <Input
          value={draft.value}
          disabled={disabled}
          aria-label={`${t("field.correction")} ${label}`}
          aria-invalid={invalid}
          data-testid="field-input"
          onChange={(e) => onChange({ ...draft, value: e.target.value, confirmed: true })}
          className={cn(invalid && "pr-9")}
        />
        {invalid && (
          <Tooltip>
            <TooltipTrigger asChild>
              <button type="button" className="absolute right-2 top-1/2 -translate-y-1/2 text-danger" aria-label={tip} data-testid="field-error">
                <AlertCircle className="h-5 w-5" />
              </button>
            </TooltipTrigger>
            <TooltipContent>{tip}</TooltipContent>
          </Tooltip>
        )}
      </div>
      {corrected && (
        <Input
          value={draft.reason}
          disabled={disabled}
          placeholder={t("field.reason")}
          aria-label={`${t("field.reason")} ${label}`}
          aria-invalid={Boolean(error)}
          data-testid="field-reason"
          onChange={(e) => onChange({ ...draft, reason: e.target.value })}
        />
      )}
      {error && <p className="text-xs text-danger">{error}</p>}
    </div>
  );
}

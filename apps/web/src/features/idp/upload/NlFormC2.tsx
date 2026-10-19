"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Sparkles, Loader2 } from "lucide-react";

const DOC_TYPE_KEYS = [
  "INVOICE",
  "SALES_REPORT",
  "KPI_OKR",
  "MEETING_MINUTES",
  "FINANCIAL_REPORT",
  "CONTRACT",
  "EMPLOYEE_LIST",
] as const;

const MIN_LENGTH = 20;

export interface NlFormC2Props {
  onSubmit: (content: string, docTypeHint?: string) => Promise<void>;
  isSubmitting: boolean;
  className?: string;
}

export function NlFormC2({ onSubmit, isSubmitting, className }: NlFormC2Props) {
  const t = useTranslations("upload.c2");
  const tIdp = useTranslations("idp");

  const [content, setContent] = useState("");
  const [docTypeHint, setDocTypeHint] = useState("");
  const [touched, setTouched] = useState(false);

  const isContentShort = content.trim().length < MIN_LENGTH;
  const showError = touched && isContentShort;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setTouched(true);
    if (isContentShort) return;
    await onSubmit(content.trim(), docTypeHint || undefined);
  };

  return (
    <form onSubmit={handleSubmit} className={className} noValidate aria-label="Natural language form">
      <p className="mb-4 text-sm text-muted-foreground">{t("description")}</p>

      <div className="mb-4">
        <label htmlFor="c2-content" className="mb-1 block text-sm font-medium text-foreground">
          {t("label")} <span className="text-rose-500" aria-hidden="true">*</span>
        </label>
        <textarea
          id="c2-content"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          onBlur={() => setTouched(true)}
          placeholder={t("placeholder")}
          rows={6}
          required
          className={`w-full rounded-md border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring resize-y ${
            showError ? "border-rose-400 focus:ring-rose-400" : "border-border"
          }`}
          aria-invalid={showError ? "true" : undefined}
          aria-describedby={showError ? "c2-error" : undefined}
        />
        <div className="mt-1 flex items-center justify-between">
          {showError && (
            <p id="c2-error" className="text-xs text-rose-500" role="alert">
              {t("minLengthHint", { min: MIN_LENGTH })}
            </p>
          )}
          <p
            className={`ml-auto text-xs tabular-nums ${content.length > 0 ? "text-muted-foreground" : "text-muted-foreground/50"}`}
          >
            {t("charCount", { n: content.length })}
          </p>
        </div>
      </div>

      <div className="mb-5">
        <label
          htmlFor="c2-doc-type-hint"
          className="mb-1 block text-sm font-medium text-foreground"
        >
          {t("docTypeHint")}
        </label>
        <select
          id="c2-doc-type-hint"
          value={docTypeHint}
          onChange={(e) => setDocTypeHint(e.target.value)}
          className="h-9 w-full max-w-xs rounded-md border border-border bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          aria-label={t("docTypeHint")}
        >
          <option value="">{tIdp("docTypeFull.auto")}</option>
          {DOC_TYPE_KEYS.map((dt) => (
            <option key={dt} value={dt}>
              {tIdp(`docTypeFull.${dt}` as Parameters<typeof tIdp>[0])}
            </option>
          ))}
        </select>
      </div>

      <button
        type="submit"
        disabled={isSubmitting || (touched && isContentShort)}
        className="inline-flex items-center gap-2 rounded-md bg-primary px-5 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
      >
        {isSubmitting ? (
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
        ) : (
          <Sparkles className="h-4 w-4" aria-hidden="true" />
        )}
        {isSubmitting ? t("submitting") : t("submit")}
      </button>
    </form>
  );
}

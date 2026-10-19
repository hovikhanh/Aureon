"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { PenLine, Loader2 } from "lucide-react";

/* -------------------------------------------------------------------------- */
/* Field definitions — all UI labels come from i18n                           */
/* -------------------------------------------------------------------------- */
type FieldType = "text" | "date" | "number";

interface FieldDef {
  key: string;
  labelKey: string; // i18n key under idp.invoiceFields / idp.contractFields etc.
  type: FieldType;
  required: boolean;
}

type SchemaMap = Record<string, FieldDef[]>;

const SCHEMAS: SchemaMap = {
  INVOICE: [
    { key: "invoice_number", labelKey: "invoiceFields.invoice_number", type: "text", required: true },
    { key: "issue_date", labelKey: "invoiceFields.issue_date", type: "date", required: true },
    { key: "subtotal", labelKey: "invoiceFields.subtotal", type: "number", required: true },
    { key: "vat_amount", labelKey: "invoiceFields.vat_amount", type: "number", required: true },
    { key: "total_amount", labelKey: "invoiceFields.total_amount", type: "number", required: true },
    { key: "payment_due", labelKey: "invoiceFields.payment_due", type: "date", required: false },
  ],
  SALES_REPORT: [
    { key: "period", labelKey: "salesFields.period", type: "text", required: true },
    { key: "total_revenue", labelKey: "salesFields.total_revenue", type: "number", required: true },
    { key: "new_customers", labelKey: "salesFields.new_customers", type: "number", required: false },
    { key: "active_customers", labelKey: "salesFields.active_customers", type: "number", required: false },
  ],
  FINANCIAL_REPORT: [
    { key: "period", labelKey: "finReportFields.period", type: "text", required: true },
    { key: "revenue", labelKey: "finReportFields.revenue", type: "number", required: true },
    { key: "gross_profit", labelKey: "finReportFields.gross_profit", type: "number", required: true },
    { key: "net_profit", labelKey: "finReportFields.net_profit", type: "number", required: true },
  ],
  CONTRACT: [
    { key: "contract_number", labelKey: "contractFields.contract_number", type: "text", required: true },
    { key: "sign_date", labelKey: "contractFields.sign_date", type: "date", required: true },
    { key: "effective_date", labelKey: "contractFields.effective_date", type: "date", required: true },
    { key: "expiry_date", labelKey: "contractFields.expiry_date", type: "date", required: true },
    { key: "contract_value", labelKey: "contractFields.contract_value", type: "number", required: false },
  ],
};

const DOC_TYPE_KEYS = ["INVOICE", "SALES_REPORT", "FINANCIAL_REPORT", "CONTRACT"] as const;

/* -------------------------------------------------------------------------- */
/* ManualFormC1                                                                */
/* -------------------------------------------------------------------------- */
export interface ManualFormC1Props {
  onSubmit: (docType: string, fields: Record<string, unknown>) => Promise<void>;
  isSubmitting: boolean;
  className?: string;
}

export function ManualFormC1({ onSubmit, isSubmitting, className }: ManualFormC1Props) {
  const t = useTranslations("upload.c1");
  const tIdp = useTranslations("idp");

  const [docType, setDocType] = useState("");
  const [fieldValues, setFieldValues] = useState<Record<string, string>>({});
  const [errors, setErrors] = useState<Record<string, boolean>>({});

  const fields: FieldDef[] = docType ? (SCHEMAS[docType] ?? []) : [];

  const handleDocTypeChange = (v: string) => {
    setDocType(v);
    setFieldValues({});
    setErrors({});
  };

  const handleFieldChange = (key: string, value: string) => {
    setFieldValues((prev) => ({ ...prev, [key]: value }));
    if (errors[key]) setErrors((prev) => ({ ...prev, [key]: false }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!docType) return;

    const newErrors: Record<string, boolean> = {};
    for (const f of fields) {
      if (f.required && !fieldValues[f.key]?.trim()) newErrors[f.key] = true;
    }
    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    const payload: Record<string, unknown> = {};
    for (const f of fields) {
      const v = fieldValues[f.key] ?? "";
      if (f.type === "number" && v !== "") payload[f.key] = parseFloat(v);
      else if (v !== "") payload[f.key] = v;
    }

    await onSubmit(docType, payload);
  };

  return (
    <form onSubmit={handleSubmit} className={className} noValidate aria-label="Manual entry form">
      <p className="mb-4 text-sm text-muted-foreground">{t("description")}</p>

      {/* Doc type selector */}
      <div className="mb-5">
        <label
          htmlFor="c1-doc-type"
          className="mb-1 block text-sm font-medium text-foreground"
        >
          {tIdp("manualDocTypeLabel")}{" "}
          <span className="text-rose-500" aria-hidden="true">*</span>
        </label>
        <select
          id="c1-doc-type"
          value={docType}
          onChange={(e) => handleDocTypeChange(e.target.value)}
          required
          className="h-9 w-full max-w-sm rounded-md border border-border bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          aria-label={tIdp("manualDocTypeLabel")}
        >
          <option value="">{tIdp("manualDocTypePlaceholder")}</option>
          {DOC_TYPE_KEYS.map((dt) => (
            <option key={dt} value={dt}>
              {tIdp(`docTypeFull.${dt}` as Parameters<typeof tIdp>[0])}
            </option>
          ))}
        </select>
      </div>

      {/* Dynamic fields */}
      {fields.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {fields.map((field) => {
            const label = tIdp(field.labelKey as Parameters<typeof tIdp>[0]);
            return (
              <div key={field.key}>
                <label
                  htmlFor={`c1-field-${field.key}`}
                  className="mb-1 block text-sm font-medium text-foreground"
                >
                  {label}
                  {field.required && (
                    <span className="ml-0.5 text-rose-500" aria-hidden="true">*</span>
                  )}
                </label>
                <input
                  id={`c1-field-${field.key}`}
                  type={field.type}
                  value={fieldValues[field.key] ?? ""}
                  onChange={(e) => handleFieldChange(field.key, e.target.value)}
                  required={field.required}
                  aria-label={label}
                  className={`h-9 w-full rounded-md border bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring ${
                    errors[field.key]
                      ? "border-rose-400 focus:ring-rose-400"
                      : "border-border"
                  }`}
                  aria-invalid={errors[field.key] ? "true" : undefined}
                />
                {errors[field.key] && (
                  <p className="mt-0.5 text-xs text-rose-500" role="alert">
                    {tIdp("fieldRequired")}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Submit */}
      {docType && (
        <div className="mt-6">
          <button
            type="submit"
            disabled={isSubmitting}
            className="inline-flex items-center gap-2 rounded-md bg-primary px-5 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
          >
            {isSubmitting ? (
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            ) : (
              <PenLine className="h-4 w-4" aria-hidden="true" />
            )}
            {isSubmitting ? t("submitting") : t("submit")}
          </button>
        </div>
      )}
    </form>
  );
}

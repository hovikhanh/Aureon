"use client";

import { useTranslations } from "next-intl";
import { AlertTriangle } from "lucide-react";
import type { DocType, ExtractedFieldOut } from "@aureon/shared-types";
import { ExtractionFieldRow } from "./ExtractionFieldRow";
import type { FieldEditState } from "./types";

export interface ExtractionFormProps {
  fields: ExtractedFieldOut[];
  fieldEdits: Record<string, FieldEditState>;
  selectedFieldId: string | null;
  docType: DocType;
  crossDocConflicts?: { rule: string; message: string }[];
  acceptedConflicts: { rule: string; note: string }[];
  onSelectField: (fieldId: string) => void;
  onChangeFieldValue: (fieldId: string, value: unknown) => void;
  onConfirmField: (fieldId: string) => void;
  onRevertField: (fieldId: string) => void;
  onChangeDocType?: (newType: DocType) => void;
  onToggleAcceptConflict?: (rule: string, note: string) => void;
  className?: string;
}

export function ExtractionForm({
  fields,
  fieldEdits,
  selectedFieldId,
  docType,
  crossDocConflicts = [],
  acceptedConflicts,
  onSelectField,
  onChangeFieldValue,
  onConfirmField,
  onRevertField,
  onChangeDocType,
  onToggleAcceptConflict,
  className,
}: ExtractionFormProps) {
  const t = useTranslations("review");
  const tDocTypes = useTranslations("inbox.docTypes");

  // Separate non-table fields and table fields
  const singleFields = fields.filter((f) => !f.table_key);
  const tableFields = fields.filter((f) => Boolean(f.table_key));

  return (
    <div className={className}>
      {/* Top Bar inside Form: Title & DocType Switcher */}
      <div className="flex items-center justify-between border-b border-border pb-3 mb-4">
        <h2 className="text-base font-semibold text-foreground">
          {t("formTitle")}
        </h2>

        {/* Change doc type dropdown */}
        <div className="flex items-center gap-2">
          <label htmlFor="doc-type-select" className="text-xs text-muted-foreground">
            {t("docTypeLabel")}:
          </label>
          <select
            id="doc-type-select"
            value={docType}
            onChange={(e) => onChangeDocType?.(e.target.value as DocType)}
            className="h-8 rounded-md border border-input bg-background px-2.5 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            aria-label={t("docTypeLabel")}
          >
            <option value="INVOICE">{tDocTypes("INVOICE")}</option>
            <option value="SALES_REPORT">{tDocTypes("SALES_REPORT")}</option>
            <option value="KPI_OKR">{tDocTypes("KPI_OKR")}</option>
            <option value="MEETING_MINUTES">{tDocTypes("MEETING_MINUTES")}</option>
            <option value="FINANCIAL_REPORT">{tDocTypes("FINANCIAL_REPORT")}</option>
            <option value="CONTRACT">{tDocTypes("CONTRACT")}</option>
            <option value="EMPLOYEE_LIST">{tDocTypes("EMPLOYEE_LIST")}</option>
            <option value="OTHER">{tDocTypes("OTHER")}</option>
          </select>
        </div>
      </div>

      {/* Cross-document conflict warning banner */}
      {crossDocConflicts.length > 0 && (
        <div className="mb-4 rounded-lg border border-amber-300 bg-amber-50/60 p-3 text-xs dark:border-amber-900/60 dark:bg-amber-950/20">
          <div className="flex items-center gap-2 font-medium text-amber-800 dark:text-amber-300">
            <AlertTriangle className="h-4 w-4 shrink-0" aria-hidden="true" />
            <span>{t("conflictBanner")}</span>
          </div>

          <div className="mt-2 space-y-2">
            {crossDocConflicts.map((c) => {
              const isAccepted = acceptedConflicts.some((ac) => ac.rule === c.rule);
              const acceptedNote =
                acceptedConflicts.find((ac) => ac.rule === c.rule)?.note || "";

              return (
                <div
                  key={c.rule}
                  className="rounded border border-amber-200 bg-card p-2 dark:border-amber-900/40"
                >
                  <p className="font-medium text-foreground">{c.rule}: {c.message}</p>
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <label className="flex items-center gap-1.5 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={isAccepted}
                        onChange={(e) =>
                          onToggleAcceptConflict?.(
                            c.rule,
                            e.target.checked ? "Accepted difference by reviewer" : "",
                          )
                        }
                        className="h-3.5 w-3.5 rounded border-input text-primary focus:ring-primary"
                      />
                      <span className="text-xs text-foreground font-medium">
                        {t("conflictAccept")}
                      </span>
                    </label>

                    {isAccepted && (
                      <input
                        type="text"
                        value={acceptedNote}
                        onChange={(e) => onToggleAcceptConflict?.(c.rule, e.target.value)}
                        placeholder={t("conflictNotePlaceholder")}
                        className="h-7 flex-1 rounded border border-input bg-background px-2 text-xs text-foreground"
                      />
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Fields list */}
      {fields.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
          {t("emptyFields")}
        </div>
      ) : (
        <div className="space-y-3">
          {/* Header/Single fields */}
          {singleFields.map((f) => {
            const editState = fieldEdits[f.id] ?? {
              fieldId: f.id,
              originalValue: f.final_value ?? f.value,
              currentValue: f.final_value ?? f.value,
              isCorrected: f.corrected,
              isConfirmed: f.confidence_band === "HIGH",
            };

            return (
              <ExtractionFieldRow
                key={f.id}
                field={f}
                editState={editState}
                isSelected={selectedFieldId === f.id}
                onSelect={() => onSelectField(f.id)}
                onChangeValue={(val) => onChangeFieldValue(f.id, val)}
                onConfirm={() => onConfirmField(f.id)}
                onRevert={() => onRevertField(f.id)}
              />
            );
          })}

          {/* Table/Line Item fields */}
          {tableFields.length > 0 && (
            <div className="mt-4 pt-3 border-t border-border">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
                {tableFields[0]?.table_key || "Line Items"}
              </h3>
              <div className="space-y-3">
                {tableFields.map((f) => {
                  const editState = fieldEdits[f.id] ?? {
                    fieldId: f.id,
                    originalValue: f.final_value ?? f.value,
                    currentValue: f.final_value ?? f.value,
                    isCorrected: f.corrected,
                    isConfirmed: f.confidence_band === "HIGH",
                  };

                  return (
                    <ExtractionFieldRow
                      key={f.id}
                      field={f}
                      editState={editState}
                      isSelected={selectedFieldId === f.id}
                      onSelect={() => onSelectField(f.id)}
                      onChangeValue={(val) => onChangeFieldValue(f.id, val)}
                      onConfirm={() => onConfirmField(f.id)}
                      onRevert={() => onRevertField(f.id)}
                    />
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

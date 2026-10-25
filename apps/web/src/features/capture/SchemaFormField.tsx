"use client";
import { useTranslations } from "next-intl";
import type { UseFormRegisterReturn } from "react-hook-form";
import { ShieldAlert } from "lucide-react";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/select";
import { ruleMessage } from "./errors";
import type { FormField } from "./types";

/** Field label from `label_key` (i18n) with the raw name as fallback. */
export function useFieldLabel() {
  const t = useTranslations();
  return (f: Pick<FormField, "name" | "label_key">) => (f.label_key && t.has(f.label_key) ? t(f.label_key) : t.has(`capture.field.${f.name}`) ? t(`capture.field.${f.name}`) : f.name);
}

/** One SCR-61 input: VN placeholders for date/number, enum → select, critical marker, inline error. */
export function SchemaFormField({ field, reg, error, id, compact = false }: { field: FormField; reg: UseFormRegisterReturn; error?: string; id: string; compact?: boolean }) {
  const t = useTranslations();
  const label = useFieldLabel()(field);
  const errId = `${id}-err`;
  const common = { id, "aria-invalid": Boolean(error), "aria-describedby": error ? errId : undefined, "data-testid": `field-${id}` };
  const input = field.enum?.length ? (
    <NativeSelect {...reg} {...common}>
      <option value="">{t("capture.form.choose")}</option>
      {field.enum.map((v) => <option key={v} value={v}>{v}</option>)}
    </NativeSelect>
  ) : (
    <Input {...reg} {...common} inputMode={["number", "money"].includes(field.value_type) ? "decimal" : undefined}
      placeholder={field.value_type === "date" ? t("capture.form.datePlaceholder") : ["number", "money"].includes(field.value_type) ? t("capture.form.numberPlaceholder") : undefined} />
  );
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className={compact ? "sr-only" : "flex items-center gap-1 text-sm font-medium"}>
        {label}{field.required && <span className="text-danger" aria-hidden>*</span>}
        {field.is_critical && <ShieldAlert className="h-3.5 w-3.5 text-warning" aria-label={t("capture.form.critical")} />}
      </label>
      {input}
      {error && <p id={errId} role="alert" className="text-xs text-danger">{ruleMessage(t, error)}</p>}
    </div>
  );
}

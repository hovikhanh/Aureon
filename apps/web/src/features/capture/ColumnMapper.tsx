"use client";
import { useTranslations } from "next-intl";
import { Sparkles } from "lucide-react";
import { NativeSelect } from "@/components/ui/select";
import { useFieldLabel } from "./SchemaFormField";
import type { FormField, ImportPreview } from "./types";

/**
 * ColumnMapper (SCR-62 step 1): file column → schema row field, AI suggestion shown with its
 * confidence (`column_mapping[header].confidence`); unmapped required fields are listed above.
 */
export function ColumnMapper({ preview, fields, mapping, onChange, disabled }: {
  preview: ImportPreview; fields: FormField[]; mapping: Record<string, string | null>; onChange: (m: Record<string, string | null>) => void; disabled?: boolean;
}) {
  const t = useTranslations();
  const label = useFieldLabel();
  const sheet = preview.sheets.find((s) => s.columns.some((c) => c.header && c.header in mapping)) ?? preview.sheets[0];
  const headers = (sheet?.columns ?? []).map((c) => c.header).filter((h): h is string => Boolean(h));
  const rowDefs = fields.filter((f) => f.repeatable_group);
  const sample = (h: string) => {
    const f = preview.column_mapping[h]?.field;
    const v = f ? preview.preview_rows[0]?.[f] : undefined;
    return v === undefined || v === null || typeof v === "object" ? "" : String(v);
  };
  return (
    <table className="w-full text-sm" data-testid="column-mapper">
      <thead><tr className="border-b text-left text-muted-foreground"><th className="py-2 pr-3 font-medium">{t("capture.import.column")}</th><th className="pr-3 font-medium">{t("capture.import.target")}</th><th /></tr></thead>
      <tbody>
        {headers.map((h) => {
          const ai = preview.column_mapping[h];
          const suggested = ai?.field && mapping[h] === ai.field;
          return (
            <tr key={h} className="border-b last:border-0" data-testid="mapper-row" data-header={h}>
              <td className="py-1.5 pr-3"><span className="font-medium">{h}</span>{sample(h) && <span className="ml-2 text-xs text-muted-foreground">{sample(h)}</span>}</td>
              <td className="pr-3">
                <NativeSelect value={mapping[h] ?? ""} disabled={disabled} aria-label={`${t("capture.import.target")} · ${h}`} onChange={(e) => onChange({ ...mapping, [h]: e.target.value || null })} className="w-60" data-testid="mapper-select">
                  <option value="">{t("capture.import.ignore")}</option>
                  {rowDefs.map((f) => <option key={f.name} value={f.name}>{label(f)}{f.required ? " *" : ""}</option>)}
                </NativeSelect>
              </td>
              <td className="text-xs">
                {suggested && ai && <span className="inline-flex items-center gap-1 rounded-full bg-ai-subtle px-2 py-0.5 text-ai" data-testid="mapper-ai"><Sparkles className="h-3 w-3" aria-hidden />{t("capture.import.aiSuggest")} · {Math.round(ai.confidence * 100)}%</span>}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

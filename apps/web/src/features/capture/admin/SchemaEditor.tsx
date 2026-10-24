"use client";
import * as React from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import { api, ApiError } from "@/lib/api-client";
import { captureError } from "../errors";
import type { ExtractionSchema, SchemaField } from "../types";

/**
 * EP-DC-31 draft editor: per-field required / critical flags + thresholds. The BE rejects
 * thresholds below 0.95 / 0.90 and un-flagging critical fields (`details.fields[]` → rows in red).
 */
export function SchemaEditor({ schema, onClose, onSaved }: { schema: ExtractionSchema; onClose: () => void; onSaved: () => void }) {
  const t = useTranslations();
  const toast = useToast();
  const [fields, setFields] = React.useState<SchemaField[]>(() => structuredClone(schema.fields));
  const [th, setTh] = React.useState({ c: String(schema.thresholds.classification_confidence_min), r: String(schema.thresholds.required_field_min) });
  const [bad, setBad] = React.useState<string[]>([]);
  const [error, setError] = React.useState<string | null>(null);
  const set = (i: number, k: "required" | "is_critical", v: boolean) => setFields((fs) => fs.map((f, j) => (j === i ? { ...f, [k]: v } : f)));
  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.patch(`/data-capture/extraction-schemas/${schema.id}`, { fields, thresholds: { classification_confidence_min: Number(th.c.replace(",", ".")), required_field_min: Number(th.r.replace(",", ".")) }, version: schema.version });
      toast.push(t("capture.admin.schema.saved"));
      onSaved();
      onClose();
    } catch (err) {
      setBad(err instanceof ApiError && Array.isArray(err.details.fields) ? (err.details.fields as string[]) : []);
      setError(captureError(t, err));
    }
  };
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-3xl" data-testid="schema-editor">
        <DialogTitle>{schema.document_type} · v{schema.schema_version}</DialogTitle>
        <DialogDescription>{t("capture.admin.schema.edit")}</DialogDescription>
        <form className="flex flex-col gap-3" onSubmit={(e) => void save(e)}>
          <fieldset className="grid gap-3 sm:grid-cols-2">
            <legend className="mb-1 text-sm font-semibold">{t("capture.admin.schema.thresholds")}</legend>
            <label className="flex flex-col gap-1 text-sm">{t("capture.admin.schema.classMin")}<Input inputMode="decimal" value={th.c} onChange={(e) => setTh({ ...th, c: e.target.value })} data-testid="th-class" /></label>
            <label className="flex flex-col gap-1 text-sm">{t("capture.admin.schema.reqMin")}<Input inputMode="decimal" value={th.r} onChange={(e) => setTh({ ...th, r: e.target.value })} data-testid="th-req" /></label>
          </fieldset>
          <div className="max-h-80 overflow-auto rounded border">
            <table className="w-full text-sm">
              <thead><tr className="border-b text-left text-muted-foreground">
                {(["fieldName", "type", "sensitivity", "required", "critical"] as const).map((c) => <th key={c} className="px-2 py-1 font-medium">{t(`capture.admin.schema.${c}`)}</th>)}
              </tr></thead>
              <tbody>
                {fields.map((f, i) => (
                  <tr key={f.name} className={`border-b last:border-0 ${bad.includes(f.name) ? "bg-danger-subtle" : ""}`} data-testid="schema-field" data-name={f.name}>
                    <td className="px-2 py-1 font-mono text-xs">{f.name}</td>
                    <td className="px-2 py-1">{f.value_type}</td>
                    <td className="px-2 py-1 tabular-nums">{f.sensitivity_level ?? 2}</td>
                    <td className="px-2 py-1"><Checkbox checked={f.required ?? false} onCheckedChange={(c) => set(i, "required", c === true)} aria-label={`${t("capture.admin.schema.required")} ${f.name}`} /></td>
                    <td className="px-2 py-1"><Checkbox checked={f.is_critical ?? false} onCheckedChange={(c) => set(i, "is_critical", c === true)} aria-label={`${t("capture.admin.schema.critical")} ${f.name}`} data-testid="field-critical" /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {error && <p role="alert" className="text-sm text-danger" data-testid="schema-error">{error}</p>}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={onClose}>{t("buttons.cancel")}</Button>
            <Button type="submit" data-testid="schema-save">{t("capture.admin.schema.save")}</Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

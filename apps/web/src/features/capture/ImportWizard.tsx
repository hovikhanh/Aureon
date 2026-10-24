"use client";
import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { ArrowLeft, Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { NativeSelect } from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";
import { api, ApiError } from "@/lib/api-client";
import { qk } from "@/lib/query-keys";
import { ColumnMapper } from "./ColumnMapper";
import { ImportRowsTable } from "./ImportRowsTable";
import { captureError } from "./errors";
import { duplicateTargets, unmappedRequired } from "./logic";
import { useFieldLabel } from "./SchemaFormField";
import type { CaptureDocument, ImportPreview } from "./types";
import { downloadErrorFile, useDocTypes, useDocument, useForm, useImport } from "./use-capture";

type Step = "map" | "preview" | "confirm";

/** SCR-62 `/data/imports/[batchId]` C5 wizard (T-636F): map (EP-DC-19) → check rows (EP-DC-20/21) → submit (EP-DC-22). */
export function ImportWizard({ batchId }: { batchId: string }) {
  const t = useTranslations();
  const q = useImport(batchId);
  if (q.isPending) return <div className="mx-auto h-96 max-w-6xl animate-pulse rounded-lg bg-muted" />;
  if (q.isError || !q.data) return <p role="alert" className="mx-auto max-w-6xl text-danger">{captureError(t, q.error)}</p>;
  return <Wizard preview={q.data} />;
}

function Wizard({ preview }: { preview: ImportPreview }) {
  const t = useTranslations();
  const toast = useToast();
  const router = useRouter();
  const client = useQueryClient();
  const label = useFieldLabel();
  const types = useDocTypes();
  const [step, setStep] = React.useState<Step>("map");
  const [docType, setDocType] = React.useState(preview.suggested_document_type?.code ?? "");
  const [sheet, setSheet] = React.useState(preview.sheets[0]?.name ?? "");
  const [headerRow, setHeaderRow] = React.useState(preview.sheets[0]?.header_row ?? 1);
  const [mapping, setMapping] = React.useState<Record<string, string | null>>(() => Object.fromEntries(Object.entries(preview.column_mapping).map(([h, m]) => [h, m.field])));
  const [busy, setBusy] = React.useState(false);
  const [serverMissing, setServerMissing] = React.useState<string[]>([]);
  const form = useForm(docType, Boolean(docType));
  const doc = useDocument(preview.document_id);
  const fields = docType ? form.data?.fields ?? [] : [];
  const missing = [...new Set([...unmappedRequired(fields, mapping), ...serverMissing.filter((f) => !Object.values(mapping).includes(f))])];
  const dupes = duplicateTargets(mapping);
  const names = (xs: string[]) => xs.map((n) => label({ name: n, label_key: `capture.field.${n}` })).join(", ");

  const saveMapping = async () => {
    setBusy(true);
    try {
      const next = await api.patch<ImportPreview>(`/data-capture/imports/${preview.batch_id}/mapping`, { document_type: docType, sheet, header_row: headerRow, mapping, version: preview.version });
      client.setQueryData(qk.captureImport(preview.batch_id), next);
      setServerMissing([]);
      setStep("preview");
    } catch (e) {
      if (e instanceof ApiError && Array.isArray(e.details.unmapped_required)) setServerMissing(e.details.unmapped_required as string[]);
      toast.push(captureError(t, e), "danger");
    } finally {
      setBusy(false);
    }
  };

  const submit = async () => {
    setBusy(true);
    try {
      const out = await api.post<{ document: CaptureDocument; rows_submitted: number; rows_excluded: number }>(`/data-capture/imports/${preview.batch_id}/submit`, { version: preview.version });
      toast.push(t("capture.import.submitted", { n: out.rows_submitted }));
      void client.invalidateQueries({ queryKey: ["capture"] });
      void client.invalidateQueries({ queryKey: ["idp"] });
      router.push("/data");
    } catch (e) {
      toast.push(captureError(t, e), "danger");
      setBusy(false);
    }
  };

  const download = async () => {
    try { await downloadErrorFile(preview.batch_id); } catch (e) { toast.push(captureError(t, e), "danger"); }
  };

  const s = preview.summary;
  const filename = doc.data?.original_filename ?? preview.sheets[0]?.name ?? "";
  const typeName = (code: string) => (t.has(`capture.docType.${code}`) ? t(`capture.docType.${code}`) : code);
  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-4" data-testid="import-wizard" data-scr="SCR-62" data-step={step}>
      <Link href="/data" className="flex items-center gap-1 text-sm text-primary"><ArrowLeft className="h-4 w-4" />{t("buttons.back")}</Link>
      <h1 className="text-2xl font-semibold">{t("capture.import.title", { file: filename })}</h1>
      <ol className="flex gap-2 text-sm" aria-label={t("capture.import.title", { file: filename })}>
        {(["map", "preview", "confirm"] as const).map((k, i) => (
          <li key={k} aria-current={step === k ? "step" : undefined} className={`rounded-full px-3 py-1 ${step === k ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"}`}>{i + 1}. {t(`capture.import.steps.${k}`)}</li>
        ))}
      </ol>
      {preview.suggested_document_type && <p className="text-sm text-ai" data-testid="import-suggested">{t("capture.import.suggested", { type: typeName(preview.suggested_document_type.code), pct: `${Math.round(preview.suggested_document_type.confidence * 100)}%` })}</p>}
      {step === "map" && (
        <Card className="flex flex-col gap-4 p-4">
          <div className="flex flex-wrap gap-4 text-sm">
            <label className="flex flex-col gap-1">{t("capture.import.docType")}
              <NativeSelect value={docType} onChange={(e) => { setDocType(e.target.value); setServerMissing([]); }} className="w-56" data-testid="import-doctype">
                <option value="">{t("capture.form.choose")}</option>
                {(types.data ?? []).filter((d) => d.channels_supported.includes("C5")).map((d) => <option key={d.code} value={d.code}>{typeName(d.code)}</option>)}
              </NativeSelect>
            </label>
            <label className="flex flex-col gap-1">{t("capture.import.sheet")}
              <NativeSelect value={sheet} onChange={(e) => setSheet(e.target.value)} className="w-48">{preview.sheets.map((x) => <option key={x.name} value={x.name}>{x.name}</option>)}</NativeSelect>
            </label>
            <label className="flex flex-col gap-1">{t("capture.import.headerRow")}
              <NativeSelect value={headerRow} onChange={(e) => setHeaderRow(Number(e.target.value))} className="w-24">{Array.from({ length: 10 }, (_, i) => <option key={i + 1} value={i + 1}>{i + 1}</option>)}</NativeSelect>
            </label>
          </div>
          <ColumnMapper preview={preview} fields={fields} mapping={mapping} onChange={setMapping} disabled={busy} />
          {missing.length > 0 && <p role="alert" className="text-sm text-danger" data-testid="unmapped-required">{t("capture.import.unmapped", { fields: names(missing) })}</p>}
          {dupes.length > 0 && <p role="alert" className="text-sm text-danger">{t("capture.import.duplicate", { fields: names(dupes) })}</p>}
          <div className="flex justify-end"><Button onClick={() => void saveMapping()} disabled={busy || !docType || missing.length > 0 || dupes.length > 0} data-testid="import-save-mapping">{busy ? t("capture.import.saving") : t("capture.import.saveMapping")}</Button></div>
        </Card>
      )}
      {step !== "map" && (
        <Card className="flex flex-col gap-3 p-4">
          <div className="flex flex-wrap items-center gap-3 text-sm" data-testid="import-summary">
            <span className="font-medium">{t("capture.import.total", { n: s.rows_total })}</span>
            <span className="text-success" data-testid="summary-valid">{t("capture.import.valid", { n: s.rows_valid })}</span>
            <span className="text-danger" data-testid="summary-invalid">{t("capture.import.invalid", { n: s.rows_invalid })}</span>
            <span className="flex-1" />
            {s.rows_invalid > 0 && <Button size="sm" variant="outline" onClick={() => void download()} data-testid="import-download-errors"><Download className="h-4 w-4" aria-hidden />{t("capture.import.downloadErrors")}</Button>}
          </div>
          <ImportRowsTable batchId={preview.batch_id} fields={fields} version={preview.version} initial={s.rows_invalid > 0 ? "invalid" : "valid"} />
          <div className="flex justify-between">
            <Button variant="outline" onClick={() => setStep("map")} disabled={busy}>{t("capture.import.back")}</Button>
            {step === "preview"
              ? <Button onClick={() => setStep("confirm")} disabled={s.rows_valid === 0} data-testid="import-next">{t("capture.import.next")}</Button>
              : <Button onClick={() => void submit()} disabled={busy || s.rows_valid === 0} data-testid="import-submit">{t("capture.import.submit", { valid: s.rows_valid, invalid: s.rows_invalid })}</Button>}
          </div>
        </Card>
      )}
    </div>
  );
}

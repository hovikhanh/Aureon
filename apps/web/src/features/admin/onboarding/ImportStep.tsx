"use client";
import * as React from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { Download, FileSpreadsheet } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import { api, ApiError } from "@/lib/api-client";
import { qk } from "@/lib/query-keys";
import { ColumnMapper } from "@/features/capture/ColumnMapper";
import { ImportRowsTable } from "@/features/capture/ImportRowsTable";
import { captureError } from "@/features/capture/errors";
import { duplicateTargets, unmappedRequired } from "@/features/capture/logic";
import type { FormField, ImportPreview } from "@/features/capture/types";
import { downloadErrorFile, postMultipart, useForm, useImport } from "@/features/capture/use-capture";
import { dropHidden } from "./logic";
import type { StepProps } from "./OnboardingWizard";

const CFG = {
  org_import: { type: "HR_ROSTER", template: "/templates/DOC-06-danh-sach-nhan-su.xlsx", ref: "org_import_id", perm: "idp:write" },
  goals_import: { type: "PLAN_KPI_OKR", template: "/templates/DOC-07-kpi-okr-q4-2026.xlsx", ref: "goals_import_id", perm: "execution:write" },
} as const;
type ImportKind = keyof typeof CFG;

/**
 * Steps 2 / 5 — C5 import (EP-DC-17 → 19 → 20/21 → 22) of doc type #4 (org) or #2 (KPI/OKR). The batch id is
 * saved in the step `refs` (`reopen_step`) so a reload resumes the same batch. Step 5 needs `execution:write`
 * (R-DEC-76): an ADM sees "done by CEO/Director" + skip.
 */
export function ImportStep({ state, viewer, patch, goTo, step }: StepProps & { step: ImportKind }) {
  const t = useTranslations();
  const toast = useToast();
  const cfg = CFG[step];
  const refs = (state.steps?.[step]?.refs ?? {}) as Record<string, unknown>;
  const batchId = typeof refs[cfg.ref] === "string" ? (refs[cfg.ref] as string) : null;
  const allowed = viewer.permissions.includes(cfg.perm) && viewer.permissions.includes("idp:write");
  const done = state.steps?.[step]?.status === "done";
  const [busy, setBusy] = React.useState(false);
  const input = React.useRef<HTMLInputElement>(null);

  const skip = async () => {
    setBusy(true);
    try { await patch(state, "skip_step", step); goTo("finish"); } catch (e) { toast.push(captureError(t, e), "danger"); } finally { setBusy(false); }
  };
  const upload = async (file: File | undefined) => {
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    form.append("document_type", cfg.type);
    setBusy(true);
    try {
      const pv = await postMultipart<ImportPreview>("/data-capture/imports", form);
      await patch(state, "reopen_step", step, { [cfg.ref]: pv.batch_id, document_id: pv.document_id });
    } catch (e) {
      toast.push(captureError(t, e), "danger");
    } finally {
      setBusy(false);
      if (input.current) input.current.value = "";
    }
  };

  return (
    <div className="flex flex-col gap-4" data-testid={`import-step-${step}`}>
      <p className="text-sm text-muted-foreground">{t(`onboarding.${step}.hint`)}</p>
      {!allowed ? (
        <div role="status" className="flex flex-wrap items-center gap-3 rounded border border-warning bg-warning-subtle p-3 text-sm" data-testid="goals-not-allowed">
          <span className="flex-1">{t("onboarding.goals_import.notAllowed")}</span>
          {step === "goals_import" && <Button size="sm" variant="outline" onClick={() => void skip()} disabled={busy} data-testid="goals-skip">{t("onboarding.skip")}</Button>}
        </div>
      ) : done ? (
        <DoneNote step={step} refs={refs} goTo={goTo} />
      ) : (
        <>
          <div className="flex flex-wrap items-center gap-2">
            <a href={cfg.template} download className="inline-flex items-center gap-1 text-sm text-primary underline" data-testid="template-link"><Download className="h-4 w-4" aria-hidden />{t("onboarding.template")}</a>
            <span className="flex-1" />
            <Button variant="outline" onClick={() => input.current?.click()} disabled={busy} data-testid="import-pick"><FileSpreadsheet className="h-4 w-4" aria-hidden />{batchId ? t("onboarding.uploadAgain") : t("onboarding.upload")}</Button>
            <input ref={input} type="file" hidden accept=".xlsx,.csv" onChange={(e) => void upload(e.target.files?.[0])} data-testid="onboarding-file" />
            {step === "goals_import" && <Button variant="ghost" onClick={() => void skip()} disabled={busy} data-testid="goals-skip">{t("onboarding.skip")}</Button>}
          </div>
          {batchId && <BatchPanel key={batchId} batchId={batchId} type={cfg.type} onSubmitted={async (r) => {
            await patch(state, "complete_step", step, { [cfg.ref]: batchId, document_id: r.document_id, rows: r.rows_submitted }); // BE refs whitelist: ids + `rows`/`count`
            goTo(step === "org_import" ? "review" : "finish");
          }} />}
        </>
      )}
    </div>
  );
}

function DoneNote({ step, refs, goTo }: { step: ImportKind; refs: Record<string, unknown>; goTo: StepProps["goTo"] }) {
  const t = useTranslations();
  return (
    <div className="flex flex-wrap items-center gap-3 text-sm" data-testid="import-done">
      <span className="text-success">{t("onboarding.importDone", { n: Number(refs.rows ?? 0) })}</span>
      <Button size="sm" onClick={() => goTo(step === "org_import" ? "review" : "finish")}>{t("onboarding.continue")}</Button>
    </div>
  );
}

interface Submitted { document_id: string; rows_submitted: number; rows_excluded: number }

/** Map (AI suggestion, level-4 columns dropped when hidden) → valid / invalid rows + error file → submit. */
function BatchPanel({ batchId, type, onSubmitted }: { batchId: string; type: string; onSubmitted: (r: Submitted) => Promise<void> }) {
  const t = useTranslations();
  const q = useImport(batchId);
  const form = useForm(type);
  if (q.isPending || form.isPending) return <div className="h-40 animate-pulse rounded bg-muted" />;
  if (q.isError || !q.data) return <p role="alert" className="text-danger">{captureError(t, q.error)}</p>;
  if (form.isError || !form.data) return <p role="alert" className="text-danger">{captureError(t, form.error)}</p>;
  return <Batch preview={q.data} type={type} fields={form.data.fields} onSubmitted={onSubmitted} />;
}

function Batch({ preview, type, fields, onSubmitted }: { preview: ImportPreview; type: string; fields: FormField[]; onSubmitted: (r: Submitted) => Promise<void> }) {
  const t = useTranslations();
  const toast = useToast();
  const client = useQueryClient();
  // AI mapping minus the columns the viewer may not see (form fields are already filtered by level, R-DEC-76)
  const [{ mapping: start, dropped }] = React.useState(() => dropHidden(Object.fromEntries(Object.entries(preview.column_mapping).map(([h, m]) => [h, m.field])), fields.map((f) => f.name)));
  const [mapping, setMapping] = React.useState<Record<string, string | null>>(start);
  const [mapped, setMapped] = React.useState(preview.version > 1);
  const [busy, setBusy] = React.useState(false);
  const missing = unmappedRequired(fields, mapping);
  const dupes = duplicateTargets(mapping);

  const save = async () => {
    setBusy(true);
    try {
      const sheet = preview.sheets[0];
      const next = await api.patch<ImportPreview>(`/data-capture/imports/${preview.batch_id}/mapping`, { document_type: type, sheet: sheet?.name ?? "", header_row: sheet?.header_row ?? 1, mapping, version: preview.version });
      client.setQueryData(qk.captureImport(preview.batch_id), next);
      setMapped(true);
    } catch (e) {
      toast.push(captureError(t, e), "danger");
    } finally { setBusy(false); }
  };
  const submit = async () => {
    setBusy(true);
    try {
      const out = await api.post<{ document: { id: string }; rows_submitted: number; rows_excluded: number }>(`/data-capture/imports/${preview.batch_id}/submit`, { version: preview.version });
      void client.invalidateQueries({ queryKey: ["capture"] });
      await onSubmitted({ document_id: out.document.id, rows_submitted: out.rows_submitted, rows_excluded: out.rows_excluded });
    } catch (e) {
      toast.push(e instanceof ApiError ? captureError(t, e) : t("errors.generic"), "danger");
      setBusy(false);
    }
  };
  const s = preview.summary;
  return (
    <div className="flex flex-col gap-3" data-testid="onboarding-batch" data-mapped={mapped}>
      {dropped.length > 0 && <p role="status" className="rounded border border-warning bg-warning-subtle p-2 text-sm" data-testid="sensitive-dropped">{t("onboarding.sensitiveDropped", { cols: dropped.join(", ") })}</p>}
      {!mapped ? (
        <>
          <ColumnMapper preview={preview} fields={fields} mapping={mapping} onChange={setMapping} disabled={busy} />
          {missing.length > 0 && <p role="alert" className="text-sm text-danger" data-testid="unmapped-required">{t("capture.import.unmapped", { fields: missing.join(", ") })}</p>}
          <div className="flex justify-end"><Button onClick={() => void save()} disabled={busy || missing.length > 0 || dupes.length > 0} data-testid="onboarding-save-mapping">{t("capture.import.saveMapping")}</Button></div>
        </>
      ) : (
        <>
          <div className="flex flex-wrap items-center gap-3 text-sm" data-testid="import-summary">
            <span className="font-medium">{t("capture.import.total", { n: s.rows_total })}</span>
            <span className="text-success" data-testid="summary-valid">{t("capture.import.valid", { n: s.rows_valid })}</span>
            <span className="text-danger" data-testid="summary-invalid">{t("capture.import.invalid", { n: s.rows_invalid })}</span>
            <span className="flex-1" />
            {s.rows_invalid > 0 && <Button size="sm" variant="outline" onClick={() => void downloadErrorFile(preview.batch_id).catch((e) => toast.push(captureError(t, e), "danger"))} data-testid="import-download-errors"><Download className="h-4 w-4" aria-hidden />{t("capture.import.downloadErrors")}</Button>}
          </div>
          <ImportRowsTable batchId={preview.batch_id} fields={fields} version={preview.version} initial={s.rows_invalid > 0 ? "invalid" : "valid"} />
          <div className="flex justify-between">
            <Button variant="outline" onClick={() => setMapped(false)} disabled={busy}>{t("capture.import.back")}</Button>
            <Button onClick={() => void submit()} disabled={busy || s.rows_valid === 0} data-testid="onboarding-submit-import">{t("capture.import.submit", { valid: s.rows_valid, invalid: s.rows_invalid })}</Button>
          </div>
        </>
      )}
    </div>
  );
}

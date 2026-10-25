"use client";
import * as React from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { FileSpreadsheet, Upload, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { NativeSelect } from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";
import { captureError } from "./errors";
import { ACCEPT_EXT, checkFiles, isTable } from "./logic";
import type { DocumentType } from "./types";
import { postMultipart, useDocTypes } from "./use-capture";

/**
 * C3 DropZone (SCR-45, FR-DC-01): drag & drop or browse, ≤ 100 files / 50 MB each, per-file inline
 * errors; optional document-type preselect; one `.xlsx` / `.csv` can go to the C5 import wizard instead.
 */
export function DropZone() {
  const t = useTranslations();
  const toast = useToast();
  const router = useRouter();
  const client = useQueryClient();
  const types: DocumentType[] = useDocTypes().data ?? [];
  const input = React.useRef<HTMLInputElement>(null);
  const [files, setFiles] = React.useState<File[]>([]);
  const [over, setOver] = React.useState(false);
  const [type, setType] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const checks = checkFiles(files);
  const ok = files.filter((_, i) => checks[i]!.ok);
  const add = (list: FileList | null) => list && setFiles((xs) => [...xs, ...Array.from(list)]);
  const reset = () => { setFiles([]); if (input.current) input.current.value = ""; };

  const send = async () => {
    const form = new FormData();
    ok.forEach((f) => form.append("files", f));
    if (type) form.append("document_type", type);
    setBusy(true);
    try {
      await postMultipart("/idp/documents", form);
      toast.push(t("capture.drop.sent", { count: ok.length }), "info");
      reset();
      void client.invalidateQueries({ queryKey: ["capture"] });
    } catch (e) {
      toast.push(captureError(t, e), "danger");
    } finally {
      setBusy(false);
    }
  };

  const toImport = async () => {
    const form = new FormData();
    form.append("file", ok[0]!);
    if (type) form.append("document_type", type);
    setBusy(true);
    try {
      const pv = await postMultipart<{ batch_id: string }>("/data-capture/imports", form);
      toast.push(t("capture.import.started"), "info");
      router.push(`/data/imports/${pv.batch_id}`);
    } catch (e) {
      toast.push(captureError(t, e), "danger");
      setBusy(false);
    }
  };

  return (
    <section aria-label={t("capture.drop.label")} className="rounded-lg border bg-card p-4" data-testid="dropzone">
      <div onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)} onDrop={(e) => { e.preventDefault(); setOver(false); add(e.dataTransfer.files); }}
        className={`flex flex-col items-center gap-2 rounded-md border-2 border-dashed px-4 py-6 text-center ${over ? "border-primary bg-muted" : "border-border"}`}>
        <Upload className="h-6 w-6 text-muted-foreground" aria-hidden />
        <p className="font-medium">{t("capture.drop.title")}</p>
        <p className="text-sm text-muted-foreground">{t("capture.drop.hint")}</p>
        <Button type="button" variant="outline" size="sm" onClick={() => input.current?.click()}>{t("capture.drop.browse")}</Button>
        <input ref={input} type="file" multiple hidden accept={ACCEPT_EXT.join(",")} onChange={(e) => add(e.target.files)} data-testid="dropzone-input" />
      </div>
      {files.length > 0 && (
        <div className="mt-3 flex flex-col gap-2">
          <ul className="max-h-48 overflow-auto text-sm" data-testid="dropzone-files">
            {files.map((f, i) => (
              <li key={`${f.name}-${i}`} className="flex items-center justify-between gap-2 border-b py-1 last:border-0">
                <span className="truncate">{f.name}</span>
                <span className="flex items-center gap-2">
                  {checks[i]!.issue && <span className="text-xs text-danger" data-testid="dropzone-issue">{t(`capture.drop.issue.${checks[i]!.issue}`)}</span>}
                  <button type="button" aria-label={t("capture.drop.remove", { name: f.name })} onClick={() => setFiles((xs) => xs.filter((_, j) => j !== i))}><X className="h-4 w-4" /></button>
                </span>
              </li>
            ))}
          </ul>
          <div className="flex flex-wrap items-center gap-2">
            <label className="flex items-center gap-2 text-sm">{t("capture.drop.preselect")}
              <NativeSelect value={type} onChange={(e) => setType(e.target.value)} className="w-56" data-testid="dropzone-type">
                <option value="">{t("capture.drop.auto")}</option>
                {types.map((d) => <option key={d.code} value={d.code}>{t.has(`capture.docType.${d.code}`) ? t(`capture.docType.${d.code}`) : d.name_vi}</option>)}
              </NativeSelect>
            </label>
            <span className="flex-1" />
            <Button type="button" variant="ghost" onClick={reset}>{t("capture.drop.clear")}</Button>
            {ok.length === 1 && isTable(ok[0]!.name) && (
              <Button type="button" variant="outline" onClick={() => void toImport()} disabled={busy} title={t("capture.drop.asImportHint")} data-testid="dropzone-import">
                <FileSpreadsheet className="h-4 w-4" aria-hidden />{t("capture.drop.asImport")}
              </Button>
            )}
            <Button type="button" onClick={() => void send()} disabled={busy || ok.length === 0} data-testid="dropzone-send">
              {busy ? t("capture.drop.sending") : t("capture.drop.send", { count: ok.length })}
            </Button>
          </div>
        </div>
      )}
    </section>
  );
}

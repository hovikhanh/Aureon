"use client";
import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useFieldArray, useForm as useRhf } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { ArrowLeft, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useToast } from "@/components/ui/toast";
import { UndoToast } from "@/components/ai/UndoToast";
import { api, ApiError } from "@/lib/api-client";
import { captureError } from "./errors";
import { errorPaths, formSchema, headerFields, rowFields, toManualBody, type FormModel } from "./logic";
import { SchemaFormField, useFieldLabel } from "./SchemaFormField";
import type { FormOut, ManualOut } from "./types";
import { invalidateWrites, undoDocument, useForm } from "./use-capture";

const blank = (fs: FormOut["fields"]) => Object.fromEntries(fs.map((f) => [f.name, ""]));

/** SCR-61 `/data/new/[documentType]` C1 SchemaForm (T-634F): fields from EP-DC-15, zod per field, EP-DC-16. */
export function SchemaForm({ documentType }: { documentType: string }) {
  const t = useTranslations();
  const q = useForm(documentType);
  if (q.isPending) return <div className="mx-auto h-96 max-w-4xl animate-pulse rounded-lg bg-muted" />;
  if (q.isError || !q.data) {
    const nf = q.error instanceof ApiError && q.error.status === 404;
    return <p role="alert" className="mx-auto max-w-4xl text-danger" data-testid="form-error">{nf ? t("capture.form.notFound") : captureError(t, q.error)}</p>;
  }
  return <FormBody form={q.data} />;
}

function FormBody({ form }: { form: FormOut }) {
  const t = useTranslations();
  const toast = useToast();
  const router = useRouter();
  const client = useQueryClient();
  const label = useFieldLabel();
  const head = headerFields(form.fields);
  const rowsDef = rowFields(form.fields);
  const typeName = t.has(`capture.docType.${form.document_type}`) ? t(`capture.docType.${form.document_type}`) : form.document_type;
  const rhf = useRhf<FormModel>({ resolver: zodResolver(formSchema(form.fields)), defaultValues: { values: blank(head), rows: rowsDef.length ? [blank(rowsDef)] : [] } });
  const rows = useFieldArray({ control: rhf.control, name: "rows" as never });
  const [done, setDone] = React.useState<ManualOut | null>(null);
  const errs = rhf.formState.errors;

  const submit = rhf.handleSubmit(async (m) => {
    try {
      const out = await api.post<ManualOut>("/data-capture/manual", toManualBody(form, m));
      invalidateWrites(client);
      if (out.status === "COMMITTED") setDone(out);
      else { toast.push(t("capture.form.sentReview"), "info"); router.push("/data"); }
    } catch (e) {
      const paths = e instanceof ApiError && e.status === 422 ? errorPaths(e.details) : [];
      paths.forEach((p) => rhf.setError(p.path as "values", { message: p.rule_code }));
      toast.push(paths.length ? t("capture.form.fixErrors") : captureError(t, e), "danger");
    }
  }, () => toast.push(t("capture.form.fixErrors"), "danger"));

  const records = done?.actions.reduce((n, a) => n + a.ids.length, 0) ?? 0;
  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-4" data-testid="schema-form" data-scr="SCR-61">
      <Link href="/data" className="flex items-center gap-1 text-sm text-primary"><ArrowLeft className="h-4 w-4" />{t("buttons.back")}</Link>
      <div>
        <h1 className="text-2xl font-semibold">{t("capture.form.title", { type: typeName })}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{t("capture.form.subtitle")}</p>
        {!form.permitted && <p className="mt-2 rounded border border-warning bg-warning-subtle px-3 py-2 text-sm" data-testid="form-not-permitted">{t("capture.form.notPermitted")}</p>}
      </div>
      <form onSubmit={(e) => void submit(e)} noValidate className="flex flex-col gap-4">
        {head.length > 0 && (
          <Card className="grid gap-4 p-4 sm:grid-cols-2">
            {head.map((f) => <SchemaFormField key={f.name} id={`values-${f.name}`} field={f} reg={rhf.register(`values.${f.name}`)} error={errs.values?.[f.name]?.message} />)}
          </Card>
        )}
        {rowsDef.length > 0 && (
          <Card className="p-4">
            <h2 className="mb-2 font-semibold">{t("capture.form.rows")}</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead><tr className="text-left text-muted-foreground">{rowsDef.map((f) => <th key={f.name} className="pb-1 pr-2 font-medium">{label(f)}{f.required && <span className="text-danger" aria-hidden>*</span>}</th>)}<th /></tr></thead>
                <tbody>
                  {rows.fields.map((r, i) => (
                    <tr key={r.id} className="align-top" data-testid="form-row">
                      {rowsDef.map((f) => <td key={f.name} className="min-w-40 py-1 pr-2"><SchemaFormField compact id={`rows-${i}-${f.name}`} field={f} reg={rhf.register(`rows.${i}.${f.name}`)} error={errs.rows?.[i]?.[f.name]?.message} /></td>)}
                      <td className="py-1"><Button type="button" size="icon" variant="ghost" aria-label={t("capture.form.removeRow", { n: i + 1 })} onClick={() => rows.remove(i)}><Trash2 className="h-4 w-4" /></Button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {rows.fields.length === 0 && <p className="py-2 text-sm text-muted-foreground">{t("capture.form.noRows")}</p>}
            </div>
            <Button type="button" variant="outline" size="sm" className="mt-2" onClick={() => rows.append(blank(rowsDef) as never)} data-testid="form-add-row"><Plus className="h-4 w-4" aria-hidden />{t("capture.form.addRow")}</Button>
          </Card>
        )}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={() => router.push("/data")}>{t("capture.form.cancel")}</Button>
          <Button type="submit" disabled={rhf.formState.isSubmitting} data-testid="form-submit">{rhf.formState.isSubmitting ? t("capture.form.submitting") : t("capture.form.submit")}</Button>
        </div>
      </form>
      {done && (
        <UndoToast message={t("capture.undo.toast", { count: records })} onClose={() => { setDone(null); router.push("/data"); }}
          onUndo={async () => { await undoDocument(done.document.id, t("capture.undo.quickReason"), "mistake"); invalidateWrites(client); toast.push(t("capture.undo.done", { count: done.actions.length })); }} />
      )}
    </div>
  );
}

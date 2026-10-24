"use client";
import * as React from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { NativeSelect } from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";
import { api } from "@/lib/api-client";
import { formatDateTime, type AppLocale } from "@/lib/format";
import { qk } from "@/lib/query-keys";
import { captureError } from "../errors";
import type { ExtractionSchema } from "../types";
import { useDocTypes } from "../use-capture";
import { SchemaEditor } from "./SchemaEditor";

const TONE = { draft: "warning", published: "success", retired: "default" } as const;

/** EP-DC-29 list by type, EP-DC-30 clone → draft, EP-DC-31 edit draft, EP-DC-32 publish. */
export function SchemasTab() {
  const t = useTranslations();
  const locale = useLocale() as AppLocale;
  const toast = useToast();
  const client = useQueryClient();
  const types = useDocTypes(true);
  const [docType, setDocType] = React.useState("");
  const [editing, setEditing] = React.useState<string | null>(null);
  const params = { document_type: docType || undefined };
  const q = useQuery({ queryKey: qk.captureSchemas(params), queryFn: ({ signal }) => api.get<ExtractionSchema[]>("/data-capture/extraction-schemas", params, signal) });
  const rows = [...(q.data ?? [])].sort((a, b) => a.document_type.localeCompare(b.document_type) || b.schema_version - a.schema_version);
  const refresh = () => void client.invalidateQueries({ queryKey: ["capture"] });
  const run = async (fn: () => Promise<ExtractionSchema>, msg: (s: ExtractionSchema) => string) => {
    try { const s = await fn(); toast.push(msg(s)); refresh(); return s; } catch (e) { toast.push(captureError(t, e), "danger"); return null; }
  };
  const clone = async (s: ExtractionSchema) => {
    const out = await run(() => api.post<ExtractionSchema>("/data-capture/extraction-schemas", { document_type: s.document_type, clone_from_id: s.id }), (x) => t("capture.admin.schema.created", { n: x.schema_version }));
    if (out) setEditing(out.id);
  };
  const publish = (s: ExtractionSchema) => run(() => api.post<ExtractionSchema>(`/data-capture/extraction-schemas/${s.id}/publish`, { version: s.version }), (x) => t("capture.admin.schema.publishedOk", { n: x.schema_version }));
  const current = rows.find((s) => s.id === editing);

  return (
    <div className="flex flex-col gap-3">
      <label className="flex items-center gap-2 text-sm">{t("capture.admin.schema.docType")}
        <NativeSelect value={docType} onChange={(e) => setDocType(e.target.value)} className="w-56" data-testid="schema-filter">
          <option value="">{t("capture.inbox.filter.all")}</option>
          {(types.data ?? []).map((d) => <option key={d.code} value={d.code}>{d.code}</option>)}
        </NativeSelect>
      </label>
      {q.isError && <p role="alert" className="text-danger">{captureError(t, q.error)}</p>}
      <table className="w-full rounded-lg border bg-card text-sm" data-testid="schemas-table">
        <thead><tr className="border-b text-left text-muted-foreground">
          {(["docType", "version", "status", "fields", "actions", "published"] as const).map((c) => <th key={c} className="px-3 py-2 font-medium">{t(`capture.admin.schema.${c}`)}</th>)}<th />
        </tr></thead>
        <tbody>
          {rows.map((s) => (
            <tr key={s.id} className="border-b align-top last:border-0" data-testid="schema-row" data-type={s.document_type} data-status={s.status}>
              <td className="px-3 py-2 font-mono">{s.document_type}</td>
              <td className="px-3 py-2 tabular-nums">v{s.schema_version}</td>
              <td className="px-3 py-2"><Badge variant={TONE[s.status]}>{t(`capture.admin.schema.statusName.${s.status}`)}</Badge></td>
              <td className="px-3 py-2 tabular-nums">{s.fields.length}</td>
              <td className="px-3 py-2 text-xs">{s.action_names.join(", ")}</td>
              <td className="px-3 py-2 whitespace-nowrap">{s.published_at ? formatDateTime(s.published_at, locale) : "—"}</td>
              <td className="whitespace-nowrap px-3 py-2 text-right">
                {s.status === "published" && <Button size="sm" variant="ghost" onClick={() => void clone(s)} data-testid="schema-clone">{t("capture.admin.schema.clone")}</Button>}
                {s.status === "draft" && <Button size="sm" variant="ghost" onClick={() => setEditing(s.id)} data-testid="schema-edit">{t("capture.admin.schema.edit")}</Button>}
                {s.status === "draft" && <Button size="sm" onClick={() => void publish(s)} data-testid="schema-publish">{t("capture.admin.schema.publish")}</Button>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {current && <SchemaEditor schema={current} onClose={() => setEditing(null)} onSaved={refresh} />}
    </div>
  );
}

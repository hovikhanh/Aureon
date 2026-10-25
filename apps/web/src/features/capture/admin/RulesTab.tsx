"use client";
import * as React from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { Checkbox } from "@/components/ui/checkbox";
import { NativeSelect } from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";
import { api } from "@/lib/api-client";
import { qk } from "@/lib/query-keys";
import { captureError } from "../errors";
import type { ExtractionSchema, ValidationRule } from "../types";
import { RuleForm } from "./RuleForm";

/** EP-DC-33 rules of a schema; EP-DC-34 add / EP-DC-35 toggle only on drafts (published = read-only). */
export function RulesTab() {
  const t = useTranslations();
  const toast = useToast();
  const client = useQueryClient();
  const schemas = useQuery({ queryKey: qk.captureSchemas({}), queryFn: ({ signal }) => api.get<ExtractionSchema[]>("/data-capture/extraction-schemas", undefined, signal) });
  const options = (schemas.data ?? []).filter((s) => s.status !== "retired");
  const [sid, setSid] = React.useState("");
  const schema = options.find((s) => s.id === sid) ?? options.find((s) => s.status === "draft") ?? options[0];
  const params = { extraction_schema_id: schema?.id };
  const rules = useQuery({ queryKey: qk.captureRules(params), enabled: Boolean(schema), queryFn: ({ signal }) => api.get<ValidationRule[]>("/data-capture/validation-rules", params, signal) });
  const editable = schema?.status === "draft";
  const refresh = () => void client.invalidateQueries({ queryKey: ["capture", "rules"] });
  const toggle = async (r: ValidationRule, on: boolean) => {
    try { await api.patch(`/data-capture/validation-rules/${r.id}`, { is_active: on, version: r.version }); toast.push(t("capture.admin.rule.saved")); refresh(); } catch (e) { toast.push(captureError(t, e), "danger"); }
  };
  return (
    <div className="flex flex-col gap-3">
      <label className="flex items-center gap-2 text-sm">{t("capture.admin.rule.schema")}
        <NativeSelect value={schema?.id ?? ""} onChange={(e) => setSid(e.target.value)} className="w-72" data-testid="rule-schema">
          {options.map((s) => <option key={s.id} value={s.id}>{s.document_type} · v{s.schema_version} · {t(`capture.admin.schema.statusName.${s.status}`)}</option>)}
        </NativeSelect>
      </label>
      {schema && !editable && <p className="text-sm text-muted-foreground" data-testid="rules-readonly">{t("capture.admin.rule.readonly")}</p>}
      {rules.isError && <p role="alert" className="text-danger">{captureError(t, rules.error)}</p>}
      {rules.data?.length === 0 && <p className="text-sm text-muted-foreground">{t("capture.admin.rule.none")}</p>}
      {(rules.data?.length ?? 0) > 0 && (
        <table className="w-full rounded-lg border bg-card text-sm" data-testid="rules-table">
          <thead><tr className="border-b text-left text-muted-foreground">
            {(["code", "kind", "op", "field", "severity", "active"] as const).map((c) => <th key={c} className="px-3 py-2 font-medium">{t(`capture.admin.rule.${c}`)}</th>)}
          </tr></thead>
          <tbody>
            {rules.data!.map((r) => (
              <tr key={r.id} className="border-b last:border-0" data-testid="rule-row" data-code={r.code}>
                <td className="px-3 py-2 font-mono">{r.code}</td>
                <td className="px-3">{t(`capture.admin.rule.kindName.${r.kind}`)}</td>
                <td className="px-3 font-mono text-xs">{String(r.expression.op ?? "")}</td>
                <td className="px-3 font-mono text-xs">{String(r.expression.field ?? (Array.isArray(r.expression.fields) ? r.expression.fields.join(", ") : ""))}</td>
                <td className="px-3">{t(`capture.admin.rule.severityName.${r.severity}`)}</td>
                <td className="px-3"><Checkbox checked={r.is_active} disabled={!editable} onCheckedChange={(c) => void toggle(r, c === true)} aria-label={`${t("capture.admin.rule.active")} ${r.code}`} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {schema && editable && <RuleForm schema={schema} onCreated={refresh} />}
    </div>
  );
}

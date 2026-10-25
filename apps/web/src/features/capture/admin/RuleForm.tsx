"use client";
import * as React from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";
import { api } from "@/lib/api-client";
import { captureError } from "../errors";
import type { ExtractionSchema } from "../types";

/** Validator ops accepted by EP-DC-34 (10 §7.2.4 rule DSL — no free code). */
export const RULE_OPS = ["required", "date_not_future", "in", "gt", "gte", "lt", "lte"] as const;
const KINDS = ["field", "master_data"] as const;
const SEVERITIES = ["warn", "fail", "blocking"] as const;

/** Build the EP-DC-34 `expression` for a single-field rule. */
export function ruleExpression(op: string, field: string, raw: string): Record<string, unknown> {
  if (op === "in") return { op, field, values: raw.split(",").map((x) => x.trim()).filter(Boolean) };
  if (["gt", "gte", "lt", "lte"].includes(op)) return { op, field, value: Number(raw.replace(/\./g, "").replace(",", ".")) };
  return { op, field };
}

export function RuleForm({ schema, onCreated }: { schema: ExtractionSchema; onCreated: () => void }) {
  const t = useTranslations();
  const toast = useToast();
  const [v, setV] = React.useState({ code: "", kind: "field", op: "required", field: schema.fields[0]?.name ?? "", severity: "fail", raw: "" });
  const [error, setError] = React.useState<string | null>(null);
  const needsValue = v.op === "in" || ["gt", "gte", "lt", "lte"].includes(v.op);
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!v.code.trim()) return setError(t("capture.errors.required"));
    try {
      await api.post("/data-capture/validation-rules", { extraction_schema_id: schema.id, code: v.code.trim(), kind: v.kind, severity: v.severity, expression: ruleExpression(v.op, v.field, v.raw) });
      toast.push(t("capture.admin.rule.created"));
      setV({ ...v, code: "", raw: "" });
      setError(null);
      onCreated();
    } catch (err) {
      setError(captureError(t, err));
    }
  };
  const sel = (k: keyof typeof v, opts: readonly string[], label: (o: string) => string, test: string) => (
    <NativeSelect value={v[k]} onChange={(e) => setV({ ...v, [k]: e.target.value })} data-testid={test}>{opts.map((o) => <option key={o} value={o}>{label(o)}</option>)}</NativeSelect>
  );
  return (
    <form onSubmit={(e) => void submit(e)} className="flex flex-wrap items-end gap-2 rounded-lg border bg-card p-3 text-sm" data-testid="rule-form">
      <label className="flex flex-col gap-1">{t("capture.admin.rule.code")}<Input value={v.code} onChange={(e) => setV({ ...v, code: e.target.value })} className="w-40" data-testid="rule-code" /></label>
      <label className="flex flex-col gap-1">{t("capture.admin.rule.kind")}{sel("kind", KINDS, (o) => t(`capture.admin.rule.kindName.${o}`), "rule-kind")}</label>
      <label className="flex flex-col gap-1">{t("capture.admin.rule.op")}{sel("op", RULE_OPS, (o) => o, "rule-op")}</label>
      <label className="flex flex-col gap-1">{t("capture.admin.rule.field")}{sel("field", schema.fields.map((f) => f.name), (o) => o, "rule-field")}</label>
      {needsValue && <label className="flex flex-col gap-1">{t(v.op === "in" ? "capture.admin.rule.values" : "capture.admin.rule.value")}<Input value={v.raw} onChange={(e) => setV({ ...v, raw: e.target.value })} className="w-48" data-testid="rule-value" /></label>}
      <label className="flex flex-col gap-1">{t("capture.admin.rule.severity")}{sel("severity", SEVERITIES, (o) => t(`capture.admin.rule.severityName.${o}`), "rule-severity")}</label>
      <Button type="submit" data-testid="rule-add">{t("capture.admin.rule.add")}</Button>
      {error && <p role="alert" className="w-full text-danger" data-testid="rule-error">{error}</p>}
    </form>
  );
}

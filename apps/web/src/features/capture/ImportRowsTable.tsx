"use client";
import * as React from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { ruleMessage } from "./errors";
import { useFieldLabel } from "./SchemaFormField";
import { isMasked, type FormField } from "./types";
import { useImportRows } from "./use-capture";

const LIMIT = 20;
type Tab = "invalid" | "valid" | "all";

/** ImportRowsTable (SCR-62 step 2, EP-DC-20): rows by status, failing cells highlighted with the rule message. */
export function ImportRowsTable({ batchId, fields, version, initial }: { batchId: string; fields: FormField[]; version: number; initial: Tab }) {
  const t = useTranslations();
  const label = useFieldLabel();
  const [tab, setTab] = React.useState<Tab>(initial);
  const [offset, setOffset] = React.useState(0);
  const q = useImportRows(batchId, { status: tab, limit: LIMIT, offset, v: version });
  const cols = fields.filter((f) => f.repeatable_group);
  const total = q.data?.meta?.pagination?.total ?? 0;
  return (
    <div className="flex flex-col gap-2" data-testid="import-rows">
      <div role="tablist" className="flex gap-1 border-b">
        {(["invalid", "valid", "all"] as const).map((k) => (
          <button key={k} role="tab" type="button" aria-selected={tab === k} onClick={() => { setTab(k); setOffset(0); }} data-testid={`rows-tab-${k}`}
            className={`-mb-px border-b-2 px-3 py-1.5 text-sm ${tab === k ? "border-primary font-medium text-primary" : "border-transparent text-muted-foreground"}`}>
            {t(`capture.import.tab${k[0]!.toUpperCase()}${k.slice(1)}` as "capture.import.tabAll")}
          </button>
        ))}
      </div>
      {q.isPending && <div className="h-40 animate-pulse rounded bg-muted" />}
      {q.data && q.data.data.length === 0 && <p className="py-4 text-sm text-muted-foreground">{tab === "invalid" ? t("capture.import.noErrors") : "—"}</p>}
      {q.data && q.data.data.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="border-b text-left text-muted-foreground"><th className="py-1 pr-2 font-medium">{t("capture.import.row")}</th>{cols.map((f) => <th key={f.name} className="pr-2 font-medium">{label(f)}</th>)}</tr></thead>
            <tbody>
              {q.data.data.map((r) => {
                const errs = new Map(r.errors.map((e) => [e.field ?? "", e]));
                return (
                  <tr key={r.row_number} className="border-b align-top last:border-0" data-testid="import-row" data-row={r.row_number} data-invalid={r.errors.length > 0}>
                    <td className="py-1 pr-2 tabular-nums">{r.row_number}</td>
                    {cols.map((f) => {
                      const e = errs.get(f.name);
                      const v = r.values[f.name];
                      return (
                        <td key={f.name} className={`pr-2 ${e ? "bg-danger-subtle" : ""}`} title={e ? ruleMessage(t, e.rule_code, e.params ?? {}) : undefined}>
                          <span className="block">{isMasked(v) ? "•••" : v === null || v === undefined ? "" : String(v)}</span>
                          {e && <span className="block text-xs text-danger" data-testid="cell-error">{ruleMessage(t, e.rule_code, e.params ?? {})}</span>}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      {total > LIMIT && (
        <div className="flex items-center justify-end gap-2 text-sm">
          <span className="text-muted-foreground">{t("capture.inbox.pageInfo", { from: offset + 1, to: Math.min(offset + LIMIT, total), total })}</span>
          <Button size="sm" variant="outline" disabled={offset === 0} onClick={() => setOffset((o) => Math.max(0, o - LIMIT))}>{t("capture.inbox.prev")}</Button>
          <Button size="sm" variant="outline" disabled={offset + LIMIT >= total} onClick={() => setOffset((o) => o + LIMIT)}>{t("capture.inbox.next")}</Button>
        </div>
      )}
    </div>
  );
}

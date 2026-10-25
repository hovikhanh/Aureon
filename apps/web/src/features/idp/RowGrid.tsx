"use client";
import * as React from "react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import { display } from "./FieldRow";
import type { ReviewField } from "./types";

const BAND: Record<string, string> = { HIGH: "", MEDIUM: "bg-warning-subtle", LOW: "bg-danger-subtle" };
const PAGE = 25;

/**
 * SCR-18b row grid (EP-DC-05 `rows`): one line per `row_index` (Excel row), cells = fields coloured
 * by confidence band; masked level-4 values show "•••". Selecting a cell focuses its field editor.
 */
export function RowGrid({ rows, activeId, onSelect, label }: { rows: Array<{ row_index: number; fields: ReviewField[] }>; activeId: string | null; onSelect: (id: string) => void; label: (f: ReviewField) => string }) {
  const t = useTranslations("capture.review");
  const [page, setPage] = React.useState(0);
  const cols = [...new Map(rows.flatMap((r) => r.fields).map((f) => [f.field_name, f])).values()];
  const shown = rows.slice(page * PAGE, page * PAGE + PAGE);
  const pages = Math.ceil(rows.length / PAGE);
  const val = (f: ReviewField | undefined) => {
    const v = f?.effective_value;
    return typeof v === "object" && v !== null && (v as { masked?: boolean }).masked ? "•••" : display(v);
  };
  return (
    <section className="flex flex-col gap-2" data-testid="row-grid">
      <h3 className="text-sm font-semibold">{t("rows", { count: rows.length })}</h3>
      <div className="overflow-x-auto rounded border">
        <table className="w-full text-xs">
          <thead><tr className="border-b bg-muted/50 text-left text-muted-foreground"><th className="px-2 py-1 font-medium">#</th>{cols.map((c) => <th key={c.field_name} className="px-2 py-1 font-medium">{label({ ...c, row_index: null })}{c.is_critical ? " *" : ""}</th>)}</tr></thead>
          <tbody>
            {shown.map((r) => {
              const by = new Map(r.fields.map((f) => [f.field_name, f]));
              return (
                <tr key={r.row_index} className="border-b last:border-0" data-testid="grid-row" data-row={r.row_index}>
                  <td className="px-2 py-1 tabular-nums text-muted-foreground">{t("row", { n: r.row_index })}</td>
                  {cols.map((c) => {
                    const f = by.get(c.field_name);
                    return (
                      <td key={c.field_name} className={cn("px-2 py-1", f && BAND[f.confidence_band ?? "HIGH"], f && f.id === activeId && "ring-2 ring-primary ring-inset", f?.is_critical && !f.is_confirmed && "font-semibold")}>
                        {f ? <button type="button" className="w-full text-left" onClick={() => onSelect(f.id)} data-testid="grid-cell">{val(f) || "—"}</button> : ""}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {pages > 1 && (
        <div className="flex items-center justify-end gap-2 text-xs">
          <button type="button" disabled={page === 0} onClick={() => setPage((p) => p - 1)} className="rounded border px-2 py-0.5 disabled:opacity-50">‹</button>
          <span className="tabular-nums">{page + 1}/{pages}</span>
          <button type="button" disabled={page + 1 >= pages} onClick={() => setPage((p) => p + 1)} className="rounded border px-2 py-0.5 disabled:opacity-50">›</button>
        </div>
      )}
    </section>
  );
}

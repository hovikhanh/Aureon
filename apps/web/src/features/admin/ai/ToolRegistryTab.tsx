"use client";
import * as React from "react";
import { useLocale, useTranslations } from "next-intl";
import { ChevronDown, ChevronRight, Columns3 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { NativeSelect } from "@/components/ui/select";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { DEFAULT_HIDDEN, TOOL_COLUMNS, agentName, filterTools, levelKey, type ToolColumn, type ToolFilter } from "./logic";
import { useAgents, useTools } from "./use-ai-admin";
import type { Tool } from "./types";

const KINDS = ["READ", "WRITE", "APPROVAL", "EXECUTION"];

/** SCR-64 Tool Registry (06 §3.4): 53 tools × 13 metadata, column toggle, filters, expandable schemas. Read only. */
export function ToolRegistryTab() {
  const t = useTranslations("aiAdmin.tools");
  const tools = useTools();
  const agents = useAgents();
  const locale = useLocale();
  const [f, setF] = React.useState<ToolFilter>({ kind: "", domain: "", agent: "", mine: false });
  const [hidden, setHidden] = React.useState<Set<ToolColumn>>(new Set(DEFAULT_HIDDEN));
  const [open, setOpen] = React.useState<string | null>(null);
  if (tools.isLoading) return <p className="text-sm text-muted-foreground">{t("loading")}</p>;
  if (tools.isError) return <p role="alert" className="text-sm text-danger">{t("error")}</p>;
  const all = tools.data ?? [];
  const domains = [...new Set(all.map((x) => x.domain ?? ""))].filter(Boolean).sort();
  const rows = filterTools(all, f);
  const cols = TOOL_COLUMNS.filter((c) => !hidden.has(c));
  const toggle = (c: ToolColumn) => setHidden((h) => { const n = new Set(h); if (n.has(c)) n.delete(c); else n.add(c); return n; });
  return (
    <section className="flex flex-col gap-3" data-testid="tool-registry">
      <div className="flex flex-wrap items-end gap-2">
        <NativeSelect aria-label={t("filter.kind")} value={f.kind} onChange={(e) => setF({ ...f, kind: e.target.value })} data-testid="tool-filter-kind">
          <option value="">{t("filter.allKinds")}</option>
          {KINDS.map((k) => <option key={k} value={k}>{k}</option>)}
        </NativeSelect>
        <NativeSelect aria-label={t("filter.domain")} value={f.domain} onChange={(e) => setF({ ...f, domain: e.target.value })} data-testid="tool-filter-domain">
          <option value="">{t("filter.allDomains")}</option>
          {domains.map((d) => <option key={d} value={d}>{d}</option>)}
        </NativeSelect>
        <NativeSelect aria-label={t("filter.agent")} value={f.agent} onChange={(e) => setF({ ...f, agent: e.target.value })} data-testid="tool-filter-agent">
          <option value="">{t("filter.allAgents")}</option>
          {(agents.data ?? []).map((a) => <option key={a.code} value={a.code}>{agentName(a, a.code, locale)}</option>)}
        </NativeSelect>
        <label className="flex h-10 items-center gap-2 text-sm">
          <Checkbox checked={f.mine} onCheckedChange={(v) => setF({ ...f, mine: v === true })} data-testid="tool-filter-mine" />
          {t("filter.mine")}
        </label>
        <Popover>
          <PopoverTrigger asChild>
            <Button variant="outline" size="sm" className="ml-auto" data-testid="tool-columns"><Columns3 className="h-4 w-4" aria-hidden />{t("columns")}</Button>
          </PopoverTrigger>
          <PopoverContent className="grid w-64 gap-1">
            {TOOL_COLUMNS.map((c) => (
              <label key={c} className="flex items-center gap-2 text-sm">
                <Checkbox checked={!hidden.has(c)} onCheckedChange={() => toggle(c)} data-testid={`tool-col-${c}`} />{t(`col.${c}`)}
              </label>
            ))}
          </PopoverContent>
        </Popover>
      </div>
      <p className="text-sm text-muted-foreground" data-testid="tool-count">{t("count", { shown: rows.length, total: all.length })}</p>
      <div className="overflow-x-auto rounded-lg border bg-card">
        <table className="w-full text-sm">
          <thead className="bg-muted/50 text-left text-xs text-muted-foreground">
            <tr>
              <th className="px-3 py-2">{t("col.name")}</th>
              {cols.map((c) => <th key={c} className="px-3 py-2" data-testid={`tool-th-${c}`}>{t(`col.${c}`)}</th>)}
            </tr>
          </thead>
          <tbody>
            {rows.map((tool) => (
              <ToolRow key={tool.name} tool={tool} cols={cols} open={open === tool.name} onToggle={() => setOpen(open === tool.name ? null : tool.name)} span={cols.length + 1} />
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function ToolRow({ tool, cols, open, onToggle, span }: { tool: Tool; cols: ToolColumn[]; open: boolean; onToggle: () => void; span: number }) {
  const t = useTranslations("aiAdmin");
  const cell = (c: ToolColumn): React.ReactNode => {
    switch (c) {
      case "kind": return <Badge variant={tool.kind === "READ" ? "default" : tool.kind === "APPROVAL" ? "danger" : "warning"}>{tool.kind}{tool.compute ? " · COMPUTE" : ""}</Badge>;
      case "permission": return <span className="font-mono text-xs">{(tool.permission ?? []).join(" + ")}</span>;
      case "autonomy": return <span data-testid="tool-autonomy">{tool.autonomy_default} / {tool.autonomy_max} → <b>{t(levelKey(tool.effective_level))}</b></span>;
      case "audit_required": return tool.audit_required ? t("tools.yes") : t("tools.no");
      default: return String((tool as Record<string, unknown>)[c] ?? "—");
    }
  };
  return (
    <>
      <tr className="border-t align-top" data-testid="tool-row" data-tool={tool.name} data-kind={tool.kind}>
        <td className="px-3 py-2">
          <button type="button" onClick={onToggle} aria-expanded={open} className="flex items-center gap-1 text-left font-mono text-xs font-medium hover:underline" data-testid="tool-expand">
            {open ? <ChevronDown className="h-3 w-3" aria-hidden /> : <ChevronRight className="h-3 w-3" aria-hidden />}{tool.name}
          </button>
          {tool.p1_frozen && <Badge variant="outline" className="mt-1" data-testid="tool-frozen">{t("tools.frozen")}</Badge>}
        </td>
        {cols.map((c) => <td key={c} className="px-3 py-2">{cell(c)}</td>)}
      </tr>
      {open && (
        <tr className="border-t bg-muted/30" data-testid="tool-detail">
          <td colSpan={span} className="px-3 py-3">
            <dl className="grid gap-2 text-xs sm:grid-cols-4">
              <div><dt className="text-muted-foreground">{t("tools.col.brd_name")}</dt><dd>{tool.brd_name ?? "—"}</dd></div>
              <div><dt className="text-muted-foreground">{t("tools.col.owner")}</dt><dd>{tool.owner ?? "—"}</dd></div>
              <div><dt className="text-muted-foreground">{t("tools.col.endpoint_ref")}</dt><dd>{tool.endpoint_ref ?? "—"}</dd></div>
              <div><dt className="text-muted-foreground">{t("tools.col.agents")}</dt><dd>{(tool.agents ?? []).join(", ") || "—"}</dd></div>
            </dl>
            <div className="mt-2 grid gap-2 md:grid-cols-2">
              <pre className="max-h-64 overflow-auto rounded border bg-card p-2 font-mono text-xs" data-testid="tool-input-schema">{JSON.stringify(tool.input_schema ?? {}, null, 2)}</pre>
              <pre className="max-h-64 overflow-auto rounded border bg-card p-2 font-mono text-xs">{JSON.stringify(tool.output_schema ?? {}, null, 2)}</pre>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

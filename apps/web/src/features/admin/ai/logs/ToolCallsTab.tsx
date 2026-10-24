"use client";
import * as React from "react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { SourceChip } from "@/components/ai/SourceChip";
import { formatDateTime, type AppLocale } from "@/lib/format";
import type { SourceRef } from "@/features/ai/types";
import { levelKey } from "../logic";
import { useLogs } from "../use-ai-admin";
import type { ToolCallLog } from "../types";
import { LOG_PAGE } from "./log-logic";
import { Pager, RequestId, useUserNames } from "./parts";

const tone = (s: string) => (s === "ok" ? "success" : s === "forbidden" ? "warning" : "danger");

/** SCR-65 Tool call tab (EP-AI-22): own query, inline error, 20/page, row → drawer (arguments, result_refs, AIAction link). */
export function ToolCallsTab({ query, onRequestId }: { query: Record<string, string>; onRequestId: (rid: string) => void }) {
  const t = useTranslations("aiLogs");
  const ta = useTranslations("aiAdmin");
  const locale = useLocale() as AppLocale;
  const [offset, setOffset] = React.useState(0);
  React.useEffect(() => setOffset(0), [query.from, query.to, query.request_id]);
  const q = useLogs<ToolCallLog>("tool-calls", { ...query, limit: LOG_PAGE, offset });
  const name = useUserNames();
  const [open, setOpen] = React.useState<ToolCallLog | null>(null);
  if (q.isError) return <p role="alert" className="text-sm text-danger" data-testid="tool-calls-error">{t("error")}</p>;
  const rows = q.data?.data ?? [];
  return (
    <section className="flex flex-col gap-2" data-testid="tool-calls">
      <div className="overflow-x-auto rounded-lg border bg-card">
        <table className="w-full text-sm">
          <thead className="bg-muted/50 text-left text-xs text-muted-foreground">
            <tr>{["time", "user", "agent", "tool", "kind", "status", "level", "latency", "request"].map((c) => <th key={c} className="px-3 py-2">{t(`col.${c}`)}</th>)}</tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} className="cursor-pointer border-t hover:bg-muted/40" onClick={() => setOpen(r)} data-testid="tool-call-row">
                <td className="px-3 py-2 whitespace-nowrap">{formatDateTime(r.created_at, locale)}</td>
                <td className="px-3 py-2">{name(r.user_id)}</td>
                <td className="px-3 py-2">{r.agent_profile_code}</td>
                <td className="px-3 py-2 font-mono text-xs">{r.tool_name}</td>
                <td className="px-3 py-2">{r.tool_kind}</td>
                <td className="px-3 py-2"><Badge variant={tone(r.status)}>{r.status}</Badge></td>
                <td className="px-3 py-2">{r.autonomy_level ? ta(levelKey(r.autonomy_level)) : "—"}</td>
                <td className="px-3 py-2">{r.latency_ms} ms</td>
                <td className="px-3 py-2"><RequestId id={r.request_id} onFilter={onRequestId} /></td>
              </tr>
            ))}
            {q.isSuccess && rows.length === 0 && <tr><td colSpan={9} className="px-3 py-6 text-center text-muted-foreground">{t("empty")}</td></tr>}
          </tbody>
        </table>
      </div>
      <Pager pagination={q.data?.meta?.pagination} offset={offset} limit={LOG_PAGE} onOffset={setOffset} />
      <Dialog open={open !== null} onOpenChange={(o) => { if (!o) setOpen(null); }}>
        <DialogContent className="max-w-2xl" data-testid="tool-call-drawer">
          <DialogTitle className="font-mono">{open?.tool_name}</DialogTitle>
          <DialogDescription>{open && `${formatDateTime(open.created_at, locale)} · ${open.status}${open.error_code ? ` (${open.error_code})` : ""}`}</DialogDescription>
          {open && (
            <div className="mt-3 flex flex-col gap-3 text-sm">
              <div><h3 className="text-xs font-medium text-muted-foreground">{t("arguments")}</h3>
                <pre className="max-h-60 overflow-auto rounded border bg-muted/30 p-2 font-mono text-xs" data-testid="tool-call-args">{JSON.stringify(open.arguments ?? {}, null, 2)}</pre></div>
              <div><h3 className="text-xs font-medium text-muted-foreground">{t("results")}</h3>
                <div className="flex flex-wrap items-center gap-1" data-testid="tool-call-refs">
                  {(open.result_refs ?? []).length ? (open.result_refs ?? []).map((s, i) => <span key={i} className="inline-flex items-center gap-1"><SourceChip n={i + 1} source={s as unknown as SourceRef} /><span className="text-xs">{String(s.label ?? s.id)}</span></span>) : "—"}
                </div></div>
              {open.ai_action_id && <Link href="/admin/ai#ai-queue" className="text-primary hover:underline" data-testid="tool-call-action">{t("actionLink")}</Link>}
              <p className="text-xs">{t("col.request")}: <RequestId id={open.request_id} /></p>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </section>
  );
}

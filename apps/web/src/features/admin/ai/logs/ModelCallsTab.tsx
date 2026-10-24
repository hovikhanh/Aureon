"use client";
import * as React from "react";
import { useLocale, useTranslations } from "next-intl";
import { Badge } from "@/components/ui/badge";
import { formatDateTime, formatNumber, type AppLocale } from "@/lib/format";
import { useLogs } from "../use-ai-admin";
import type { ModelCallLog } from "../types";
import { LOG_PAGE, shortHash, usd4 } from "./log-logic";
import { Pager, RequestId } from "./parts";

/** SCR-65 Model call tab (EP-AI-23): provider/model, fallback, tokens, cost USD (4 dp), latency, status, short `prompt_sha256`. */
export function ModelCallsTab({ query, onRequestId }: { query: Record<string, string>; onRequestId: (rid: string) => void }) {
  const t = useTranslations("aiLogs");
  const locale = useLocale() as AppLocale;
  const [offset, setOffset] = React.useState(0);
  React.useEffect(() => setOffset(0), [query.from, query.to, query.request_id]);
  const q = useLogs<ModelCallLog>("model-calls", { ...query, limit: LOG_PAGE, offset });
  if (q.isError) return <p role="alert" className="text-sm text-danger" data-testid="model-calls-error">{t("error")}</p>;
  const rows = q.data?.data ?? [];
  return (
    <section className="flex flex-col gap-2" data-testid="model-calls">
      <div className="overflow-x-auto rounded-lg border bg-card">
        <table className="w-full text-sm">
          <thead className="bg-muted/50 text-left text-xs text-muted-foreground">
            <tr>{["time", "model", "fallback", "tokens", "cost", "latency", "status", "hash", "request"].map((c) => <th key={c} className="px-3 py-2">{t(`col.${c}`)}</th>)}</tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} className="border-t" data-testid="model-call-row">
                <td className="px-3 py-2 whitespace-nowrap">{formatDateTime(r.created_at, locale)}</td>
                <td className="px-3 py-2"><div>{r.provider}</div><div className="font-mono text-xs text-muted-foreground">{r.model}</div></td>
                <td className="px-3 py-2">{r.fallback_from ? <Badge variant="warning">{t("fallbackFrom", { from: r.fallback_from })}</Badge> : "—"}</td>
                <td className="px-3 py-2">{formatNumber(r.tokens_in, locale, 0)} / {formatNumber(r.tokens_out, locale, 0)}</td>
                <td className="px-3 py-2 font-mono text-xs" data-testid="model-cost">{usd4(r.cost_usd)}</td>
                <td className="px-3 py-2">{formatNumber(r.latency_ms, locale, 0)} ms</td>
                <td className="px-3 py-2"><Badge variant={r.status === "ok" ? "success" : "danger"}>{r.status}</Badge></td>
                <td className="px-3 py-2 font-mono text-xs" title={r.prompt_sha256 ?? undefined}>{shortHash(r.prompt_sha256)}</td>
                <td className="px-3 py-2"><RequestId id={r.request_id} onFilter={onRequestId} /></td>
              </tr>
            ))}
            {q.isSuccess && rows.length === 0 && <tr><td colSpan={9} className="px-3 py-6 text-center text-muted-foreground">{t("empty")}</td></tr>}
          </tbody>
        </table>
      </div>
      <Pager pagination={q.data?.meta?.pagination} offset={offset} limit={LOG_PAGE} onOffset={setOffset} />
    </section>
  );
}

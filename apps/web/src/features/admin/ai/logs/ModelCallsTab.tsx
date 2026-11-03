"use client";
import * as React from "react";
import { useLocale, useTranslations } from "next-intl";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/select";
import { formatDateTime, formatNumber, type AppLocale } from "@/lib/format";
import { useLogs, useUsage } from "../use-ai-admin";
import type { ModelCallLog } from "../types";
import { EMPTY_MODEL_FILTER, isUnpriced, LOG_PAGE, MODEL_CALL_STATUSES, modelCallQuery, shortHash, usd4, type ModelFilter } from "./log-logic";
import { Pager, RequestId } from "./parts";

/**
 * SCR-65 Model call tab (EP-AI-23): provider/model, fallback, tokens, cost USD (4 dp), latency, status, short `prompt_sha256`.
 * M5: provider / model / status filters (EP-AI-23 already accepts them); providers offered are the ones with calls this month
 * (EP-AI-15 `group_by=provider`) so the list is real data, not a hard-coded catalogue.
 */
export function ModelCallsTab({ query, onRequestId }: { query: Record<string, string>; onRequestId: (rid: string) => void }) {
  const t = useTranslations("aiLogs");
  const locale = useLocale() as AppLocale;
  const [offset, setOffset] = React.useState(0);
  const [mf, setMf] = React.useState<ModelFilter>(EMPTY_MODEL_FILTER);
  React.useEffect(() => setOffset(0), [query.from, query.to, query.request_id, mf.provider, mf.model, mf.status]);
  const providers = (useUsage({ group_by: "provider", period: new Date().toISOString().slice(0, 7) }).data?.rows ?? []).map((r) => r.key);
  const q = useLogs<ModelCallLog>("model-calls", { ...modelCallQuery(query, mf), limit: LOG_PAGE, offset });
  const filters = (
    <div className="flex flex-wrap items-end gap-3" data-testid="model-call-filters">
      <div className="flex flex-col gap-1"><Label htmlFor="mc-provider">{t("filter.provider")}</Label>
        <NativeSelect id="mc-provider" value={mf.provider} onChange={(e) => setMf({ ...mf, provider: e.target.value })} data-testid="mc-provider">
          <option value="">{t("filter.all")}</option>
          {[...new Set([...providers, ...(mf.provider ? [mf.provider] : [])])].map((p) => <option key={p} value={p}>{p}</option>)}
        </NativeSelect></div>
      <div className="flex min-w-56 flex-col gap-1"><Label htmlFor="mc-model">{t("filter.model")}</Label>
        <Input id="mc-model" value={mf.model} placeholder="qwen2.5:7b-instruct" onChange={(e) => setMf({ ...mf, model: e.target.value })} data-testid="mc-model" /></div>
      <div className="flex flex-col gap-1"><Label htmlFor="mc-status">{t("filter.status")}</Label>
        <NativeSelect id="mc-status" value={mf.status} onChange={(e) => setMf({ ...mf, status: e.target.value })} data-testid="mc-status">
          <option value="">{t("filter.all")}</option>
          {MODEL_CALL_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
        </NativeSelect></div>
    </div>
  );
  if (q.isError) return <section className="flex flex-col gap-2">{filters}<p role="alert" className="text-sm text-danger" data-testid="model-calls-error">{t("error")}</p></section>;
  const rows = q.data?.data ?? [];
  return (
    <section className="flex flex-col gap-2" data-testid="model-calls">
      {filters}
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
                <td className="px-3 py-2 font-mono text-xs" data-testid="model-cost">
                  {isUnpriced(r) ? <Badge variant="warning" title={t("unpricedHint")} data-testid="model-unpriced">{t("unpriced")}</Badge> : usd4(r.cost_usd)}
                </td>
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

/** SCR-65 pure helpers (unit-tested): default 7-day range, date → ISO query, short hash, page size 20. */
export const LOG_PAGE = 20;
export interface LogFilter { from: string; to: string; requestId: string }

const day = (d: Date) => d.toISOString().slice(0, 10);
export function defaultRange(now: Date): { from: string; to: string } {
  return { from: day(new Date(now.getTime() - 7 * 86_400_000)), to: day(now) };
}
/** `YYYY-MM-DD` inputs → ISO 8601 UTC bounds (`to` inclusive to end of day); empty `request_id` dropped. */
export function rangeQuery(f: LogFilter): Record<string, string> {
  const q: Record<string, string> = {};
  if (f.from) q.from = `${f.from}T00:00:00Z`;
  if (f.to) q.to = `${f.to}T23:59:59Z`;
  if (f.requestId) q.request_id = f.requestId;
  return q;
}
export const shortHash = (h: string | null | undefined) => (h ? `${h.slice(0, 8)}…` : "—");
export const usd4 = (v: number) => `$${v.toFixed(4)}`;
export const COST_GROUPS = ["provider", "model", "task_kind", "agent", "user"] as const;

/** Providers that run on-prem: $0 is their real price, not a missing one (07 §6.5, R-DEC-155). */
export const LOCAL_PROVIDERS: readonly string[] = ["ollama"];
export const MODEL_CALL_STATUSES = ["ok", "error", "timeout", "forbidden"] as const;

/** A cloud call that used tokens but was stored at $0 → its cost is unknown (no `MODEL_PRICING_JSON` price). */
export function isUnpriced(r: { provider: string; cost_usd: number; tokens_in: number; tokens_out: number }): boolean {
  return r.cost_usd === 0 && r.tokens_in + r.tokens_out > 0 && !LOCAL_PROVIDERS.includes(r.provider);
}

export interface ModelFilter { provider: string; model: string; status: string }
export const EMPTY_MODEL_FILTER: ModelFilter = { provider: "", model: "", status: "" };

/** Shared range query + the EP-AI-23 filters the model-call tab adds (empty ones dropped). */
export function modelCallQuery(base: Record<string, string>, f: ModelFilter): Record<string, string> {
  const q = { ...base };
  if (f.provider) q.provider = f.provider;
  if (f.model.trim()) q.model = f.model.trim();
  if (f.status) q.status = f.status;
  return q;
}

export interface UsageTotals { calls: number; tokensIn: number; tokensOut: number; costUsd: number; errors: number; errorRate: number; unpriced: number }

/** Totals over EP-AI-15 rows (each row's `error_rate` is per row → weight it by its `calls`). */
export function usageTotals(rows: readonly { calls: number; tokens_in: number; tokens_out: number; cost_usd: number; error_rate: number; unpriced_calls?: number }[]): UsageTotals {
  const t = rows.reduce(
    (a, r) => ({
      calls: a.calls + r.calls, tokensIn: a.tokensIn + r.tokens_in, tokensOut: a.tokensOut + r.tokens_out,
      costUsd: a.costUsd + r.cost_usd, errors: a.errors + Math.round(r.error_rate * r.calls), unpriced: a.unpriced + (r.unpriced_calls ?? 0),
    }),
    { calls: 0, tokensIn: 0, tokensOut: 0, costUsd: 0, errors: 0, unpriced: 0 },
  );
  return { ...t, errorRate: t.calls ? t.errors / t.calls : 0 };
}

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

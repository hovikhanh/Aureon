/**
 * Mock EP-AI-22 tool-call / EP-AI-23 model-call logs (append-only, default last 7 days, `from > to`
 * → 400, filters + pagination) and EP-AI-15 usage (`group_by` provider/model/task_kind/user/agent,
 * `period=YYYY-MM`, bad format → 400). All `ai:admin`.
 */
import { MockHttpError, ok, parsePage, type Page } from "./http";
import type { MockRequest, Route } from "./router";
import { aiStore, BUDGET_USD } from "./ai-admin-store";

function range(q: URLSearchParams): { from: string; to: string } {
  const from = q.get("from") ?? new Date(Date.now() - 7 * 86_400_000).toISOString();
  const to = q.get("to") ?? new Date(Date.now() + 60_000).toISOString();
  if (from > to) throw new MockHttpError(400, "BAD_REQUEST", "from must be <= to", { param: "from" });
  return { from, to };
}
function pageOf<T extends { created_at: string }>(rows: T[], page: Page, key: (r: T) => string | number = (r) => r.created_at): Response {
  const order = page.sortBy ? page.order : "desc";
  const sorted = [...rows].sort((a, b) => (key(a) < key(b) ? -1 : key(a) > key(b) ? 1 : 0) * (order === "desc" ? -1 : 1));
  const data = sorted.slice(page.offset, page.offset + page.limit);
  return ok(data, 200, { pagination: { total: rows.length, limit: page.limit, offset: page.offset, has_next: page.offset + data.length < rows.length } });
}
const matches = (q: URLSearchParams, r: Record<string, unknown>, keys: string[]) => keys.every((k) => !q.get(k) || String(r[k]) === q.get(k));

function toolCalls(req: MockRequest): Response {
  const q = req.query;
  const { from, to } = range(q);
  const page = parsePage(q, ["created_at"]);
  const rows = aiStore().toolCalls.filter((r) => r.created_at >= from && r.created_at <= to
    && matches(q, r as unknown as Record<string, unknown>, ["tool_name", "tool_kind", "agent_profile_code", "status", "user_id", "request_id", "ai_action_id"]));
  return pageOf(rows, page);
}
function modelCalls(req: MockRequest): Response {
  const q = req.query;
  const { from, to } = range(q);
  const page = parsePage(q, ["created_at", "estimated_cost_micro_usd", "latency_ms"]);
  const rows = aiStore().modelCalls.filter((r) => r.created_at >= from && r.created_at <= to
    && matches(q, r as unknown as Record<string, unknown>, ["provider", "model", "task_kind", "caller_module", "agent_profile_code", "status", "request_id"]));
  const key = page.sortBy === "latency_ms" ? (r: (typeof rows)[number]) => r.latency_ms : page.sortBy === "estimated_cost_micro_usd" ? (r: (typeof rows)[number]) => r.cost_usd : undefined;
  return pageOf(rows, page, key);
}

const GROUPS = { provider: "provider", model: "model", task_kind: "task_kind", user: "user_id", agent: "agent_profile_code" } as const;
const p95 = (xs: number[]) => [...xs].sort((a, b) => a - b)[Math.max(0, Math.ceil(xs.length * 0.95) - 1)] ?? 0;
function usage(req: MockRequest): Response {
  const q = req.query;
  const group = (q.get("group_by") ?? "provider") as keyof typeof GROUPS;
  if (!(group in GROUPS)) throw new MockHttpError(422, "VALIDATION_ERROR", "invalid group_by", { field: "group_by" });
  const period = q.get("period") ?? new Date().toISOString().slice(0, 7);
  if (!/^\d{4}-(0[1-9]|1[0-2])$/.test(period)) throw new MockHttpError(400, "BAD_REQUEST", "period must be YYYY-MM", { param: "period" });
  const calls = aiStore().modelCalls.filter((m) => m.created_at.slice(0, 7) === period);
  const by = new Map<string, typeof calls>();
  for (const m of calls) {
    const k = String(m[GROUPS[group]] ?? "—");
    by.set(k, [...(by.get(k) ?? []), m]);
  }
  const round = (x: number) => Number(x.toFixed(4));
  const rows = [...by.entries()].map(([key, ms]) => ({ key, calls: ms.length, tokens_in: ms.reduce((s, m) => s + m.tokens_in, 0), tokens_out: ms.reduce((s, m) => s + m.tokens_out, 0),
    cost_usd: round(ms.reduce((s, m) => s + m.cost_usd, 0)), error_rate: round(ms.filter((m) => m.status !== "ok").length / ms.length), p95_ms: p95(ms.map((m) => m.latency_ms)) }))
    .sort((a, b) => b.cost_usd - a.cost_usd);
  const used = round(calls.reduce((s, m) => s + m.cost_usd, 0));
  const pct = Number(((used / BUDGET_USD) * 100).toFixed(1));
  return ok({ budget_usd: BUDGET_USD, used_usd: used, used_pct: pct, period: `${period}-01`, over_budget: pct >= 100, warn_80pct: pct >= 80, rows });
}

export const AI_LOG_ROUTES: readonly Route[] = [
  { method: "GET", pattern: "/ai/usage", permission: "ai:admin", handler: usage },
  { method: "GET", pattern: "/ai/tool-calls", permission: "ai:admin", handler: toolCalls },
  { method: "GET", pattern: "/ai/model-calls", permission: "ai:admin", handler: modelCalls },
];

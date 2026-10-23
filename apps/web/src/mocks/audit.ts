/**
 * Mock append-only audit log (T-617F, EP-52 / EP-ADM-12) — every mock mutation of the admin
 * screens appends here (shared by all sessions); filters `action`, `actor_type`, `from`, `to`
 * like the backend (`from > to` → 400).
 */
import type { MockClaims } from "./fixtures";
import { MockHttpError, paginate, parsePage } from "./http";
import type { MockRequest } from "./router";

export interface MockAudit {
  id: string;
  occurred_at: string;
  actor_type: "USER" | "AI" | "SYSTEM";
  actor_user_id: string | null;
  actor_role: string | null;
  action: string;
  target_schema: string | null;
  target_table: string | null;
  target_id: string | null;
  why: string | null;
}

// on globalThis: `next dev` re-evaluates server modules when it compiles another page
const G = globalThis as typeof globalThis & { __aureonMockAudit?: MockAudit[] };
const rows: MockAudit[] = (G.__aureonMockAudit ??= []);

export function recordAudit(c: MockClaims, action: string, table: string, id: string, why: string | null = null): void {
  rows.unshift({
    id: globalThis.crypto.randomUUID(), occurred_at: new Date().toISOString(), actor_type: "USER", actor_user_id: c.sub,
    actor_role: c.role, action, target_schema: action.split(".")[0] ?? null, target_table: table, target_id: id, why,
  });
}

export function resetAudit(): void {
  rows.length = 0;
}

export function listAudit(req: MockRequest): Response {
  const q = req.query;
  const action = q.get("action");
  const actor = q.get("actor_type");
  const from = q.get("from") ?? q.get("occurred_from");
  const to = q.get("to") ?? q.get("occurred_to");
  if (from && to && from > to) throw new MockHttpError(400, "BAD_REQUEST", "from must be <= to", { param: "from" });
  const out = rows.filter((r) => (!action || r.action === action) && (!actor || r.actor_type === actor)
    && (!from || r.occurred_at >= from) && (!to || r.occurred_at <= to));
  return paginate(out as unknown as Record<string, unknown>[], parsePage(q, ["occurred_at"]));
}

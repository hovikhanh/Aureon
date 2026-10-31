/**
 * Mock BFF router (T-604, R-DEC-25): `METHOD path → handler` table served by
 * `app/api/backend/[...path]` when `API_MODE=mock`. Same envelope / errors / pagination as the
 * backend (`http.ts`); permission per route as the real `require_permission` (default deny →
 * 403 FORBIDDEN_ROLE); unknown route → 404 NOT_FOUND. Data = `seed_snapshot.json` + per-session
 * in-memory store. Chat = fake SSE in the EP-111 order (start → tool_call → tool_result →
 * token… → done).
 */
import type { MockClaims } from "./fixtures";
import { MockHttpError, fail, ok, paginate, parsePage } from "./http";
import { chatStream, conversationMessages, listConversations } from "./chat";
import { SNAPSHOT } from "./fixtures";
import { metricOut } from "./reporting-shared";
import { REPORTING_ROUTES } from "./reporting";
import { metricVisible, sessionFor } from "./store";
import { ORG_ROUTES } from "./org";
import { ADMIN_ROUTES } from "./admin";
import { listAudit } from "./audit";
import { WORK_ROUTES } from "./work";
import { PROJECT_ROUTES } from "./work-projects";
import { WORKFLOW_ROUTES } from "./workflow";
import { GOALS_ROUTES } from "./goals";
import { CAPTURE_ROUTES } from "./capture";
import { AI_ADMIN_ROUTES } from "./ai_admin";
import { ONBOARDING_ROUTES } from "./onboarding";
import { FINANCE_ROUTES } from "./finance";
import { SALES_ROUTES } from "./sales";
import { MEETINGS_ROUTES } from "./meetings";

export interface MockRequest {
  method: string;
  path: string;
  query: URLSearchParams;
  headers: Headers;
  body: unknown;
  claims: MockClaims;
  params: Record<string, string>;
}

type Handler = (req: MockRequest) => Response | Promise<Response>;

export interface Route {
  method: string;
  pattern: string;
  permission: string;
  handler: Handler;
}

function requireIdempotency(req: MockRequest): void {
  if (!req.headers.get("idempotency-key")?.trim()) {
    throw new MockHttpError(400, "BAD_REQUEST", "Idempotency-Key header is required", { header: "Idempotency-Key" });
  }
}

export const ROUTES: readonly Route[] = [
  {
    method: "GET", pattern: "/dashboard/metrics", permission: "dashboard:read",
    handler: ({ claims, query }) => {
      const status = query.get("status");
      const rows = SNAPSHOT.metrics.filter((m) => metricVisible(claims, m.code, m.pillar) && (!status || m.status === status));
      return ok(rows.map(metricOut));
    },
  },
  {
    method: "GET", pattern: "/dashboard/metrics/:code", permission: "dashboard:read",
    handler: ({ claims, params }) => {
      const m = SNAPSHOT.metrics.find((x) => x.code === params.code);
      if (!m) return fail(404, "NOT_FOUND", "metric not found");
      if (!metricVisible(claims, m.code, m.pillar)) return fail(403, "FORBIDDEN_SCOPE", "metric outside scope");
      return ok({ ...metricOut(m), name: m.code, formula_display: "", direction: "up", thresholds: { warning: 0, critical: 0 },
        trend: [{ period_key: m.period_key, value: m.value }], breakdown: [], related_alerts: [], data_source: { module: "mock", entities: [] } });
    },
  },
  {
    method: "GET", pattern: "/dashboard/alerts", permission: "dashboard:read",
    handler: ({ claims, query }) => {
      const rows = sessionFor(claims.sub).alerts.filter((a) => metricVisible(claims, a.metric_code, a.pillar));
      return paginate(rows as unknown as Record<string, unknown>[], parsePage(query, ["raised_at", "severity"]));
    },
  },
  {
    method: "POST", pattern: "/dashboard/alerts/:id/acknowledge", permission: "dashboard:write",
    handler: (req) => {
      requireIdempotency(req);
      const a = sessionFor(req.claims.sub).alerts.find((x) => x.id === req.params.id);
      if (!a || !metricVisible(req.claims, a.metric_code, a.pillar)) return fail(404, "NOT_FOUND", "alert not found");
      if (a.status !== "open") return fail(409, "CONFLICT_STATE", "alert is not open", { status: a.status });
      a.status = "acknowledged";
      a.acknowledged_by = req.claims.sub;
      return ok(a);
    },
  },
  { method: "GET", pattern: "/ai/conversations", permission: "ai:query", handler: listConversations },
  { method: "GET", pattern: "/ai/conversations/:id/messages", permission: "ai:query", handler: conversationMessages },
  {
    method: "POST", pattern: "/ai/chat/stream", permission: "ai:query",
    handler: (req) => {
      requireIdempotency(req);
      return chatStream(req);
    },
  },
  // M1.2 admin screens (T-617F): org structure, users/roles, audit, notifications.
  { method: "GET", pattern: "/platform/audit-logs", permission: "platform:read", handler: listAudit },
  ...ORG_ROUTES,
  ...ADMIN_ROUTES,
  // M1.3 work (T-625F): tasks, projects, milestones, workload, approvals.
  ...WORK_ROUTES,
  ...PROJECT_ROUTES,
  ...WORKFLOW_ROUTES,
  // M1.4 goals (T-626F..T-628F): strategy tree, KPI, OKR, check-ins.
  ...GOALS_ROUTES,
  ...CAPTURE_ROUTES,
  // M1.6 AI Control Center + actions (T-644F..T-647F)
  ...AI_ADMIN_ROUTES,
  ...ONBOARDING_ROUTES,
  // M2.1 Reporting v3 (T-707F): SCR-40 3 cấp dashboard + 4 ô Executive.
  ...REPORTING_ROUTES,
  // M2.2 business (T-715F): Finance Lite + Sales pipeline.
  ...FINANCE_ROUTES,
  ...SALES_ROUTES,
  // M2.3 meetings (T-717F): EP-DC-38 C2 natural-language / short voice note.
  ...MEETINGS_ROUTES,
];

function match(pattern: string, path: string): Record<string, string> | null {
  const p = pattern.split("/").filter(Boolean);
  const s = path.split("/").filter(Boolean);
  if (p.length !== s.length) return null;
  const params: Record<string, string> = {};
  for (const [i, seg] of p.entries()) {
    const actual = s[i] ?? "";
    if (seg.startsWith(":")) params[seg.slice(1)] = decodeURIComponent(actual);
    else if (seg !== actual) return null;
  }
  return params;
}

/** Dispatch one BFF request. `path` is relative to `/api/v1` (e.g. `/dashboard/metrics`). */
export async function handleMock(req: Omit<MockRequest, "params">): Promise<Response> {
  const candidates = ROUTES.map((r) => ({ r, params: match(r.pattern, req.path) })).filter((x) => x.params !== null);
  if (candidates.length === 0) return fail(404, "NOT_FOUND", `mock route not implemented: ${req.path}`, { mode: "mock" });
  // a literal segment beats a `:param` one (`/notifications/read-all` vs `/:id/read`)
  const hit = candidates.filter((x) => x.r.method === req.method).sort((a, b) => Object.keys(a.params ?? {}).length - Object.keys(b.params ?? {}).length)[0];
  if (!hit) return fail(405, "BAD_REQUEST", "method not allowed", { allowed: candidates.map((x) => x.r.method).join(",") });
  if (hit.r.permission && !req.claims.permissions.includes(hit.r.permission)) {
    return fail(403, "FORBIDDEN_ROLE", "permission denied", { required: hit.r.permission });
  }
  try {
    return await hit.r.handler({ ...req, params: hit.params ?? {} });
  } catch (err) {
    if (err instanceof MockHttpError) return fail(err.status, err.code, err.message, err.details);
    return fail(500, "INTERNAL_ERROR", "internal error");
  }
}

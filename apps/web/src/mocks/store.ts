/**
 * In-memory mock store (T-604), one per session (`sub`), seeded from the snapshot. Writes
 * (acknowledge alert, chat turns) live only in this process; restart = fresh demo state.
 */
import { SNAPSHOT, mockId, type MockClaims, type SnapshotMetric } from "./fixtures";
import { resetOrgStore } from "./org";
import { resetAdminStore } from "./admin";
import { resetAudit } from "./audit";
import { resetWorkStore } from "./work-store";

export interface MockAlert {
  id: string;
  alert_code: string;
  metric_code: string;
  pillar: SnapshotMetric["pillar"];
  severity: "warning" | "critical";
  status: "open" | "acknowledged" | "resolved" | "dismissed";
  scope: Record<string, string>;
  value: number | null;
  threshold: number;
  period_key: string;
  raised_at: string;
  acknowledged_by: string | null;
  message_key: string;
  message_params: Record<string, unknown>;
}

export interface MockMessage {
  id: string;
  sender: "user" | "assistant";
  content: string;
  sources: Record<string, unknown>[];
  function_calls: { tool: string; status: string; latency_ms: number }[];
  truncated: boolean;
  created_at: string;
}

export interface MockSession {
  alerts: MockAlert[];
  conversations: { id: string; title: string | null; last_message_at: string | null; messages: MockMessage[] }[];
}

const RAISED_AT = `${SNAPSHOT.reference_date}T01:00:00Z`;

function seedAlerts(): MockAlert[] {
  return SNAPSHOT.metrics
    .filter((m) => m.status === "warning" || m.status === "critical")
    .map((m) => ({
      id: mockId("alert", m.code),
      alert_code: `ALR-${m.code.replace("METRIC-", "")}`,
      metric_code: m.code,
      pillar: m.pillar,
      severity: m.status as "warning" | "critical",
      status: "open",
      scope: {},
      value: m.value,
      threshold: m.value ?? 0,
      period_key: m.period_key,
      raised_at: RAISED_AT,
      acknowledged_by: null,
      message_key: `alert.${m.code}`,
      message_params: { value: m.value, unit: m.unit },
    }));
}

const sessions = new Map<string, MockSession>();

export function sessionFor(sub: string): MockSession {
  let s = sessions.get(sub);
  if (!s) {
    s = { alerts: seedAlerts(), conversations: [] };
    sessions.set(sub, s);
  }
  return s;
}

/** Test hook: drop every session (fresh demo state). */
export function resetMockStore(): void {
  sessions.clear();
  resetOrgStore();
  resetAdminStore();
  resetAudit();
  resetWorkStore();
}

// ---- scope (mirror of dashboard_service.visible_pillars / metric_visible, R-DEC-12a) ----
const PILLAR_DOMAIN: Record<string, string> = { F: "finance", O: "hr", C: "sales", U: "product", S: "risk" };

export function visiblePillars(c: MockClaims): Set<string> {
  const scoped = (p: string) => c.scope_pillars.length === 0 || c.scope_pillars.includes(p);
  const seen = new Set(Object.entries(PILLAR_DOMAIN).filter(([p, d]) => c.permissions.includes(`${d}:query`) && scoped(p)).map(([p]) => p));
  if (!seen.has("F") && c.permissions.includes("finance:query")) seen.add("F");
  return seen;
}

function seesFullFinance(c: MockClaims): boolean {
  if (c.role === "CEO") return true;
  return c.role === "DIR" && (c.scope_pillars.length === 0 || c.scope_pillars.some((p) => p === "F" || p === "S"));
}

export function metricVisible(c: MockClaims, code: string, pillar: string | null): boolean {
  if (pillar === null || !visiblePillars(c).has(pillar)) return false;
  return pillar !== "F" || seesFullFinance(c) || code === "METRIC-FIN-01";
}

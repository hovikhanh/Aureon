import type { PillarCode, PillarStatus } from "./types";

/**
 * 5 pillar cards from domain dashboards (10 §5 — no aggregate endpoint, FR-DSH-07 isolation).
 * PIL-O = EP-80 (hr) + EP-49 (execution); status = worst of the two (10 §5, OQ-06).
 * `top` = headline metric; `trend`/`series` = sparkline from the API `*_trend` (FE never computes KPIs).
 */
export interface PillarSource {
  domain: string;
  permission: string;
  trend: string;
  series: string;
}

export interface PillarDef {
  code: PillarCode;
  slug: string;
  top: string;
  sources: PillarSource[];
}

export const PILLARS: readonly PillarDef[] = [
  { code: "F", slug: "finance", top: "METRIC-FIN-01",
    sources: [{ domain: "finance", permission: "finance:query", trend: "revenue_trend", series: "revenue" }] },
  { code: "O", slug: "operations", top: "METRIC-OPS-01",
    sources: [
      { domain: "hr", permission: "hr:query", trend: "headcount_trend", series: "headcount" },
      { domain: "execution", permission: "execution:query", trend: "ontime_trend", series: "tasks_on_time_pct" },
    ] },
  { code: "C", slug: "customer", top: "METRIC-CUS-01",
    sources: [{ domain: "sales", permission: "sales:query", trend: "pipeline_trend", series: "pipeline_value" }] },
  { code: "U", slug: "product", top: "METRIC-PRD-03",
    sources: [{ domain: "product", permission: "product:query", trend: "churn_trend", series: "churn_rate_pct" }] },
  { code: "S", slug: "strategy", top: "METRIC-RSK-01",
    sources: [{ domain: "risk", permission: "risk:query", trend: "risk_score_trend", series: "aggregate_risk_score" }] },
];

export function pillarBySlug(slug: string): PillarDef | undefined {
  return PILLARS.find((p) => p.slug === slug);
}

/**
 * Pillar scope per role v3 (CLAUDE §1.4, R-DEC-12). Out-of-scope pillars are hidden.
 * CEO + DIR span all five pillars at the role level; a DIR's khối is enforced server-side
 * (R-DEC-12a scope_pillars) per request — the FE menu intersects with `permissions`.
 * MGR/EMP/REV/ADM have no executive pillar card.
 */
export const ROLE_PILLARS: Record<string, readonly PillarCode[]> = {
  CEO: ["F", "O", "C", "U", "S"],
  DIR: ["F", "O", "C", "U", "S"],
};

/** Visible pillars = role scope ∩ permission on at least one source endpoint. */
export function visiblePillars(role: string, perms: readonly string[]): PillarDef[] {
  const scope = ROLE_PILLARS[role] ?? [];
  return PILLARS.filter((p) => scope.includes(p.code) && p.sources.some((s) => perms.includes(s.permission)));
}

const RANK: Record<PillarStatus, number> = { no_data: -1, ok: 0, warning: 1, critical: 2 };

export function worstStatus(statuses: PillarStatus[]): PillarStatus {
  if (!statuses.length) return "no_data";
  return statuses.reduce((a, b) => (RANK[b] > RANK[a] ? b : a));
}

/** Demo reference period (DEC-230 layout is defined on T9/2026; `DEMO_REFERENCE_DATE` = 2026-10-20). */
export const DEFAULT_PERIOD = process.env.NEXT_PUBLIC_DASHBOARD_PERIOD ?? "2026-09";

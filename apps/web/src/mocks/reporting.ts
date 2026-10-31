/**
 * M2.1 Reporting v3 mock (T-707F) — EP-RPT-01..05 (10 §7.2.6). Same wire format as the BE
 * ReportingService: executive/department/employee dashboards + executive-tiles preference.
 * Groups mirror BE `catalog.GROUP_OF` (R-DEC-82); out-of-scope metrics/pillars are absent.
 */
import { ok, fail, MockHttpError } from "./http";
import type { MockRequest, Route } from "./router";
import { SNAPSHOT, COMPUTED_AT, metricOut, groupOf } from "./reporting-shared";
import { sessionFor, metricVisible } from "./store";

const SEI_CODE = "METRIC-STR-02";
const DEFAULT_TILES = ["METRIC-FIN-01", "METRIC-FIN-03", "METRIC-STR-01", "METRIC-OPS-01"];
const MAX_TILES = 4;

function tilesOf(sub: string): { tiles: string[]; version: number } {
  const s = sessionFor(sub) as unknown as { execTiles?: { tiles: string[]; version: number } };
  return s.execTiles ?? { tiles: [...DEFAULT_TILES], version: 0 };
}

function setTiles(sub: string, tiles: string[], version: number): void {
  const s = sessionFor(sub) as unknown as { execTiles?: { tiles: string[]; version: number } };
  s.execTiles = { tiles, version };
}

function requireIdem(req: MockRequest): void {
  if (!req.headers.get("idempotency-key")?.trim()) {
    throw new MockHttpError(400, "BAD_REQUEST", "Idempotency-Key required", { header: "Idempotency-Key" });
  }
}

function visibleMetrics(claims: MockRequest["claims"]) {
  return SNAPSHOT.metrics.filter((m) => metricVisible(claims, m.code, m.pillar));
}

function executive(req: MockRequest): Response {
  if (req.claims.role !== "CEO" && req.claims.role !== "DIR") {
    return fail(403, "FORBIDDEN_ROLE", "executive dashboard is CEO/DIR only");
  }
  const ms = visibleMetrics(req.claims);
  const byCode = new Map(ms.map((m) => [m.code, m]));
  const { tiles: tileCodes } = tilesOf(req.claims.sub);
  const tiles = tileCodes.filter((c) => byCode.has(c)).map((c) => metricOut(byCode.get(c)!));
  const sei = byCode.has(SEI_CODE) ? metricOut(byCode.get(SEI_CODE)!) : null;
  const risks = sessionFor(req.claims.sub).alerts.filter((a) => metricVisible(req.claims, a.metric_code, a.pillar));
  return ok({
    summary_line: `${risks.length} rủi ro mở`,
    tiles, sei,
    decisions_waiting: { count: 0, items: [] },
    open_risks: { count: risks.length, items: risks.slice(0, 5) },
    ai_done: { count: 0, items: [] },
    generated_at: COMPUTED_AT,
  });
}

function department(req: MockRequest): Response {
  if (!["CEO", "DIR", "MGR"].includes(req.claims.role)) {
    return fail(403, "FORBIDDEN_ROLE", "department dashboard is DIR/MGR only");
  }
  const kpis = visibleMetrics(req.claims).filter((m) => ["OPS", "STR", "PPL"].includes(groupOf(m.code) ?? "")).map(metricOut);
  const atRisk = kpis.filter((m) => m.status === "warning" || m.status === "critical").length;
  return ok({
    department_id: req.query.get("department_id"),
    kpis,
    okrs: { at_risk_count: atRisk, total: kpis.length },
    workload: { overloaded_count: 0, heatmap_ref: "/work/workload" },
    late_projects: 1,
    due_tasks: { overdue: 0, today: 0, this_week: 0 },
    generated_at: COMPUTED_AT,
  });
}

function employee(req: MockRequest): Response {
  void req; // EMP/MGR/CEO/DIR đều xem được; dữ liệu cá nhân tĩnh trong mock
  return ok({
    my_tasks: { overdue: 0, today: 0, this_week: 0 },
    my_goals: { kpis: 0, krs: 0 },
    pending_checkins: [],
    workload_week_pct: null,
    generated_at: COMPUTED_AT,
  });
}

function getTiles(req: MockRequest): Response {
  return ok(tilesOf(req.claims.sub));
}

function putTiles(req: MockRequest): Response {
  requireIdem(req);
  const body = (req.body ?? {}) as { tiles?: unknown; version?: unknown };
  const tiles = Array.isArray(body.tiles) ? body.tiles.map(String) : [];
  if (tiles.length > MAX_TILES) return fail(422, "VALIDATION_ERROR", "at most 4 tiles", { field: "tiles" });
  if (new Set(tiles).size !== tiles.length) return fail(422, "VALIDATION_ERROR", "duplicate tile", { field: "tiles" });
  for (const code of tiles) {
    const m = SNAPSHOT.metrics.find((x) => x.code === code);
    if (!m) return fail(422, "VALIDATION_ERROR", "unknown metric", { metric_code: code });
    if (!metricVisible(req.claims, m.code, m.pillar)) return fail(422, "BUSINESS_RULE_VIOLATION", "out of scope", { metric_code: code, reason: "out_of_scope" });
  }
  const cur = tilesOf(req.claims.sub);
  if (cur.version !== Number(body.version)) return fail(409, "CONFLICT_STATE", "version mismatch", { expected: String(cur.version) });
  const version = cur.version + 1;
  setTiles(req.claims.sub, tiles, version);
  return ok({ tiles, version });
}

// Perm (R-DEC-84, làm rõ 2026-10-31): Executive + tiles = dashboard:read/write (CEO/DIR);
// Department/Employee = execution:read (MGR/EMP sẵn có) — ma trận 02 §5.2 không đổi.
export const REPORTING_ROUTES: readonly Route[] = [
  { method: "GET", pattern: "/reporting/dashboards/executive", permission: "dashboard:read", handler: executive },
  { method: "GET", pattern: "/reporting/dashboards/department", permission: "execution:read", handler: department },
  { method: "GET", pattern: "/reporting/dashboards/employee", permission: "execution:read", handler: employee },
  { method: "GET", pattern: "/reporting/preferences/executive-tiles", permission: "dashboard:read", handler: getTiles },
  { method: "PUT", pattern: "/reporting/preferences/executive-tiles", permission: "dashboard:write", handler: putTiles },
];

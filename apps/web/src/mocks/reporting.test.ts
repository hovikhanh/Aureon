/** T-707F — mock BFF `/reporting/*` (EP-RPT-01..05) mirror BE: scope 3 cấp, 4 ô Executive. */
import { beforeEach, describe, expect, it } from "vitest";
import { MOCK_USERS, claimsFor } from "./fixtures";
import { handleMock } from "./router";
import { resetMockStore } from "./store";

const user = (email: string) => claimsFor(MOCK_USERS.find((u) => u.email === email)!);
const CEO = user("ceo@abc.demo");
const EMP = user("employee@abc.demo");
const MGR = user("manager@abc.demo");
const IDEM = { "idempotency-key": "k-1" };
type Err = { code: string; details: Record<string, unknown> };

async function call<T = unknown>(path: string, opts: { method?: string; claims?: ReturnType<typeof user>; body?: unknown; headers?: Record<string, string> } = {}) {
  const [p, q = ""] = path.split("?");
  const res = await handleMock({ method: opts.method ?? "GET", path: p!, query: new URLSearchParams(q), headers: new Headers(opts.headers), body: opts.body, claims: opts.claims ?? CEO });
  const json = res.status === 204 ? null : ((await res.json()) as { data: T; meta?: Record<string, unknown>; error?: Err });
  return { status: res.status, json };
}

beforeEach(() => resetMockStore());

describe("EP-RPT-01 executive dashboard", () => {
  it("CEO: 4 ô mặc định + SEI + rủi ro mở", async () => {
    const r = await call<{ tiles: { metric_code: string }[]; sei: { metric_code: string } | null; open_risks: { count: number } }>("/reporting/dashboards/executive", { claims: CEO });
    expect(r.status).toBe(200);
    expect(r.json!.data.tiles.length).toBeLessThanOrEqual(4);
    expect(r.json!.data.sei?.metric_code).toBe("METRIC-STR-02");
    expect(r.json!.data.open_risks.count).toBeGreaterThanOrEqual(0);
  });
  it("EMP bị cấm (403 executive)", async () => {
    const r = await call("/reporting/dashboards/executive", { claims: EMP });
    expect(r.status).toBe(403);
  });
});

describe("EP-RPT-02 department dashboard", () => {
  it("chỉ KPI nhóm OPS/STR/PPL; EMP 403", async () => {
    const r = await call<{ kpis: { group: string }[] }>("/reporting/dashboards/department", { claims: MGR });
    expect(r.status).toBe(200);
    for (const k of r.json!.data.kpis) expect(["OPS", "STR", "PPL"]).toContain(k.group);
    expect((await call("/reporting/dashboards/department", { claims: EMP })).status).toBe(403);
  });
});

describe("EP-RPT-03 employee dashboard", () => {
  it("EMP xem được", async () => {
    expect((await call("/reporting/dashboards/employee", { claims: EMP })).status).toBe(200);
  });
});

describe("EP-RPT-04/05 executive-tiles preference", () => {
  it("GET mặc định 4 mã, version 0", async () => {
    const r = await call<{ tiles: string[]; version: number }>("/reporting/preferences/executive-tiles", { claims: CEO });
    expect(r.json!.data.tiles).toHaveLength(4);
    expect(r.json!.data.version).toBe(0);
  });
  it("PUT hợp lệ tăng version; thiếu Idempotency-Key → 400", async () => {
    const body = { tiles: ["METRIC-FIN-01", "METRIC-FIN-02"], version: 0 };
    expect((await call("/reporting/preferences/executive-tiles", { method: "PUT", claims: CEO, body })).status).toBe(400);
    const ok = await call<{ version: number }>("/reporting/preferences/executive-tiles", { method: "PUT", claims: CEO, body, headers: IDEM });
    expect(ok.status).toBe(200);
    expect(ok.json!.data.version).toBe(1);
  });
  it(">4 ô → 422; version lệch → 409; trùng → 422", async () => {
    const tooMany = { tiles: ["METRIC-FIN-01", "METRIC-FIN-02", "METRIC-FIN-03", "METRIC-FIN-04", "METRIC-FIN-05"], version: 0 };
    expect((await call("/reporting/preferences/executive-tiles", { method: "PUT", claims: CEO, body: tooMany, headers: IDEM })).status).toBe(422);
    const dup = { tiles: ["METRIC-FIN-01", "METRIC-FIN-01"], version: 0 };
    expect((await call("/reporting/preferences/executive-tiles", { method: "PUT", claims: CEO, body: dup, headers: IDEM })).status).toBe(422);
    const stale = { tiles: ["METRIC-FIN-01"], version: 99 };
    expect((await call("/reporting/preferences/executive-tiles", { method: "PUT", claims: CEO, body: stale, headers: IDEM })).status).toBe(409);
  });
});

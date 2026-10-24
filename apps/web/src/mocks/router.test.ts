/** TC-M11-09 (T-604, 10 §1.2–§1.5) — mock BFF envelope / errors / pagination / fake SSE order. */
import { beforeEach, describe, expect, it } from "vitest";
import { parseSseChunk } from "@/lib/sse";
import { MOCK_USERS, SNAPSHOT, claimsFor } from "./fixtures";
import { handleMock } from "./router";
import { resetMockStore } from "./store";
import { SSE_ORDER } from "./chat";

const user = (email: string) => claimsFor(MOCK_USERS.find((u) => u.email === email)!);
const CEO = user("ceo@abc.demo");

function call(path: string, opts: { method?: string; claims?: ReturnType<typeof user>; body?: unknown; headers?: Record<string, string> } = {}) {
  const [p, q = ""] = path.split("?");
  return handleMock({
    method: opts.method ?? "GET", path: p!, query: new URLSearchParams(q), headers: new Headers(opts.headers),
    body: opts.body, claims: opts.claims ?? CEO,
  });
}

beforeEach(() => resetMockStore());

describe("mock BFF envelope", () => {
  it("wraps success in {data} with X-Request-Id and no-store", async () => {
    const res = await call("/dashboard/metrics");
    expect(res.status).toBe(200);
    expect(res.headers.get("x-request-id")).toMatch(/^[0-9a-f-]{36}$/);
    expect(res.headers.get("cache-control")).toBe("no-store");
    const body = (await res.json()) as { data: { metric_code: string; status: string }[] };
    // CEO sees every pillar metric; cross-pillar ones (DQ-01, pillar null) are not dashboard cards
    expect(body.data).toHaveLength(SNAPSHOT.metrics.filter((m) => m.pillar !== null).length);
    const runway = body.data.find((m) => m.metric_code === "METRIC-FIN-03");
    expect(runway?.status).toBe("critical"); // seed v3 main alert (08 §5)
  });

  it("returns {error:{code,message,details}} for unknown route, wrong method, missing permission", async () => {
    const r404 = await call("/nope/things");
    expect(r404.status).toBe(404);
    expect(((await r404.json()) as { error: { code: string } }).error.code).toBe("NOT_FOUND");
    const r405 = await call("/dashboard/metrics", { method: "DELETE" });
    expect(r405.status).toBe(405);
    const adm = await call("/dashboard/metrics", { claims: user("admin@abc.demo") });
    expect(adm.status).toBe(403);
    const err = (await adm.json()) as { error: { code: string; message: string; details: Record<string, unknown> } };
    expect(err.error).toEqual({ code: "FORBIDDEN_ROLE", message: "permission denied", details: { required: "dashboard:read" } });
  });

  it("scopes metrics like the backend (DIR {O} sees only FIN-01 of pillar F)", async () => {
    const res = await call("/dashboard/metrics", { claims: user("hr@abc.demo") });
    const codes = ((await res.json()) as { data: { metric_code: string; pillar: string }[] }).data;
    expect(codes.filter((m) => m.pillar === "F").map((m) => m.metric_code)).toEqual(["METRIC-FIN-01"]);
    expect(codes.some((m) => m.pillar === "C")).toBe(false);
  });

  it("paginates with meta.pagination and validates limit/sort_by", async () => {
    const res = await call("/dashboard/alerts?limit=5&offset=10&sort_by=raised_at&order=desc");
    const body = (await res.json()) as { data: unknown[]; meta: { pagination: Record<string, unknown> } };
    expect(body.meta.pagination).toEqual({ total: 13, limit: 5, offset: 10, has_next: false });
    expect(body.data).toHaveLength(3);
    expect((await call("/dashboard/alerts?limit=101")).status).toBe(400);
    expect((await call("/dashboard/alerts?sort_by=password")).status).toBe(400);
  });

  it("acknowledge needs Idempotency-Key, mutates the session store, then CONFLICT_STATE", async () => {
    const list = (await (await call("/dashboard/alerts?limit=1")).json()) as { data: { id: string }[] };
    const path = `/dashboard/alerts/${list.data[0]!.id}/acknowledge`;
    expect((await call(path, { method: "POST", body: {} })).status).toBe(400);
    const okRes = await call(path, { method: "POST", body: {}, headers: { "idempotency-key": "k1" } });
    expect(((await okRes.json()) as { data: { status: string } }).data.status).toBe("acknowledged");
    const again = await call(path, { method: "POST", body: {}, headers: { "idempotency-key": "k2" } });
    expect(again.status).toBe(409);
    // another session still sees it open — the store is per session
    const other = { ...CEO, sub: "other-session" };
    const rows = (await (await call("/dashboard/alerts?limit=100", { claims: other })).json()) as { data: { id: string; status: string }[] };
    expect(rows.data.find((a) => a.id === list.data[0]!.id)?.status).toBe("open");
  });
});

describe("mock chat SSE", () => {
  it("emits start → tool_call → tool_result → token… → done with grounded numbers", async () => {
    const res = await call("/ai/chat/stream", { method: "POST", body: { message: "Tình hình?" }, headers: { "idempotency-key": "c1" } });
    expect(res.headers.get("content-type")).toBe("text/event-stream");
    const { events } = parseSseChunk(await res.text());
    const order = events.map((e) => e.event).filter((e, i, xs) => e !== "token" || xs[i - 1] !== "token");
    expect(order).toEqual([...SSE_ORDER]);
    const done = events.at(-1)!.data as { answer: string; sources: { value: number | null }[] };
    for (const n of done.answer.match(/\d+(\.\d+)?(?= )/g) ?? []) {
      expect(done.sources.some((s) => String(s.value) === n), n).toBe(true);
    }
    const convs = (await (await call("/ai/conversations")).json()) as { data: { id: string }[] };
    expect(convs.data).toHaveLength(1);
    const msgs = (await (await call(`/ai/conversations/${convs.data[0]!.id}/messages`)).json()) as { data: unknown[] };
    expect(msgs.data).toHaveLength(2);
  });

  it("rejects an empty message with VALIDATION_ERROR", async () => {
    const res = await call("/ai/chat/stream", { method: "POST", body: { message: " " }, headers: { "idempotency-key": "c2" } });
    expect(res.status).toBe(422);
  });
});

describe("M1.4 goals routes (T-626F..T-628F)", () => {
  it("serves every EP-STR/KPI/OKR/PRF path behind execution:read / execution:write (REV/ADM → FORBIDDEN_ROLE)", async () => {
    const paths = ["/goals/tree", "/goals/strategies", "/goals/strategic-objectives", "/goals/initiatives", "/kpis", "/objectives", "/goals/check-ins", "/goals/check-ins/due"];
    for (const p of paths) expect((await call(p)).status, p).toBe(200);
    for (const p of paths) expect((await call(p, { claims: user("reviewer@abc.demo") })).status, p).toBe(403);
    expect((await call("/kpis", { method: "POST", body: {}, claims: user("admin@abc.demo") })).status).toBe(403);
    expect((await call("/execution/kpis")).status).toBe(404); // R-DEC-58: old paths removed, no alias
  });
});

import { expect, request, test } from "./fixtures";
import { devPassword, login } from "./helpers";

/**
 * T-903 — NFR automation on the REAL stack (security + PWA). `@real-only`.
 * Complements the existing NFR specs that already run green on the compose stack:
 *   - responsive.spec.ts  → 1440 / 1280 / 768 / 390, no horizontal scroll (06 breakpoints)
 *   - a11y-m2.spec.ts     → WCAG AA structure (landmarks, single H1, named nav, ⌘K modal)
 *   - scripts/perf_m2_gate.sh → NFR-PERF-01 dashboard p95 < 3s, NFR-PERF-02 chat TTFT < 2s
 * This spec adds the SECURITY (RBAC default-deny, 401 on no-token, NFR-07 cache headers) and
 * PWA (installable manifest + service worker) assertions against the live API/web.
 */
const API = process.env.E2E_API_URL ?? "http://localhost:4000/api/v1";

async function tokenFor(email: string): Promise<string> {
  const ctx = await request.newContext();
  const res = await ctx.post(`${API}/auth/login`, { data: { email, password: devPassword(email) } });
  expect(res.ok(), await res.text()).toBeTruthy();
  const token = (await res.json()).data.access_token as string;
  await ctx.dispose();
  return token;
}

test.describe("T-903 NFR — security (real)", { tag: "@real-only" }, () => {
  test("no token → 401 (default deny, NFR-SEC)", async () => {
    const ctx = await request.newContext();
    const res = await ctx.get(`${API}/reporting/dashboards/executive`);
    expect(res.status()).toBe(401);
    await ctx.dispose();
  });

  test("EMP → finance = 403 FORBIDDEN (RBAC, pillar out of scope)", async () => {
    const token = await tokenFor("employee@abc.demo");
    const ctx = await request.newContext();
    const res = await ctx.get(`${API}/finance/invoices`, { headers: { Authorization: `Bearer ${token}` } });
    expect(res.status()).toBe(403);
    await ctx.dispose();
  });

  test("dashboard carries NFR-07 cache headers (private + Vary: Authorization + X-Request-Id)", async () => {
    const token = await tokenFor("ceo@abc.demo");
    const ctx = await request.newContext();
    const res = await ctx.get(`${API}/reporting/dashboards/executive`, { headers: { Authorization: `Bearer ${token}` } });
    expect(res.status()).toBe(200);
    const h = res.headers();
    expect(h["cache-control"]).toContain("private");
    expect((h["vary"] ?? "").toLowerCase()).toContain("authorization");
    expect(h["x-request-id"]).toBeTruthy();
    await ctx.dispose();
  });

  test("health endpoint is no-store", async () => {
    const ctx = await request.newContext();
    const res = await ctx.get(`${API}/health`);
    expect(res.status()).toBe(200);
    expect(res.headers()["cache-control"]).toContain("no-store");
    await ctx.dispose();
  });
});

test.describe("T-903 NFR — PWA (real)", { tag: "@real-only" }, () => {
  test("web app ships an installable manifest (SCR-28 mobile PWA)", async ({ page }) => {
    await login(page, "ceo@abc.demo");
    const href = await page.locator('link[rel="manifest"]').first().getAttribute("href");
    expect(href, "manifest link present").toBeTruthy();
    const res = await page.request.get(href!);
    expect(res.ok()).toBeTruthy();
    const manifest = await res.json();
    expect(manifest.name || manifest.short_name).toBeTruthy();
    expect(Array.isArray(manifest.icons) && manifest.icons.length).toBeTruthy();
    expect(manifest.start_url).toBeTruthy();
    expect(["standalone", "fullscreen", "minimal-ui"]).toContain(manifest.display);
  });

  test("service worker asset is served (offline shell)", async ({ page }) => {
    const res = await page.request.get("/sw.js");
    expect(res.ok()).toBeTruthy();
    expect((res.headers()["content-type"] ?? "")).toMatch(/javascript/);
  });
});

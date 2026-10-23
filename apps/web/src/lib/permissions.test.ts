/** TC-M11-12 (unit) + TC-M11-13 (map) — IA v3 nav/routes per role (06 §3.2/§3.4, T-607). */
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { SNAPSHOT, type RoleCode } from "@/mocks/fixtures";
import { LEGACY_ROUTES, legacyRedirect } from "./legacy-routes";
import { ROUTE_RULES, canAccess, landingFor, safeCallback, visibleNav } from "./permissions";

/** The real JWT permission matrix of each role (exported from the BE by the seed snapshot). */
const perms = (r: RoleCode) => SNAPSHOT.role_permissions[r];
const nav = (r: RoleCode) => visibleNav(r, perms(r)).map((i) => i.key);

describe("sidebar per role (06 §3.2/§3.4, default deny)", () => {
  it.each([
    ["CEO", ["home", "ask", "goals", "work", "meetings", "data", "business", "knowledge", "admin"]],
    ["DIR", ["home", "ask", "goals", "work", "meetings", "data", "business", "knowledge"]],
    ["MGR", ["home", "ask", "goals", "work", "meetings", "data", "business", "knowledge"]],
    ["EMP", ["home", "ask", "goals", "work", "meetings", "data", "business", "knowledge"]],
    ["REV", ["home", "ask", "data", "business", "knowledge"]],
    ["ADM", ["home", "ask", "data", "knowledge", "admin"]],
    ["AI", []],
  ] as const)("%s", (role, keys) => {
    expect(nav(role)).toEqual(keys);
  });

  it("has 8 main items + Quản trị and no product/risk entry (R-DEC-16)", () => {
    const all = visibleNav("CEO", perms("CEO"));
    expect(all.filter((i) => i.group === "main")).toHaveLength(8);
    expect(all.filter((i) => i.group === "admin").map((i) => i.href)).toEqual(["/admin"]);
    expect(all.some((i) => /product|risk/.test(i.href))).toBe(false);
  });

  it("an unknown role or missing permission sees nothing beyond the open items", () => {
    expect(visibleNav("GUEST", perms("CEO"))).toEqual([]);
    expect(visibleNav("EMP", []).map((i) => i.key)).toEqual(["home", "knowledge"]);
  });
});

describe("route guard (06 §3.4)", () => {
  it.each([
    ["/home/pillar/finance", "CEO", true], ["/home/pillar/finance", "MGR", false],
    ["/data/review", "REV", true], ["/data/review/abc", "MGR", true], ["/data/review", "EMP", false],
    ["/work/approvals", "MGR", true], ["/work/approvals", "EMP", false],
    ["/business/finance/invoices", "REV", true], ["/business/finance/invoices", "EMP", false],
    ["/business/hr/employees", "EMP", true], ["/business/hr/employees", "ADM", false],
    ["/admin/audit", "ADM", true], ["/admin/audit", "CEO", false], ["/admin", "CEO", true],
    ["/goals", "REV", false], ["/ask", "AI", false], ["/403", "EMP", true],
  ] as const)("%s as %s → %s", (path, role, ok) => {
    expect(canAccess(path, role, perms(role))).toBe(ok);
  });

  it("every human role lands on /home; the AI actor has no UI", () => {
    for (const r of ["CEO", "DIR", "MGR", "EMP", "REV", "ADM"] as const) expect(landingFor(r, perms(r))).toBe("/home");
    expect(landingFor("AI", perms("AI"))).toBe("/403");
  });
});

describe("v2.1 → v3 redirects (TC-M11-13 map)", () => {
  it.each([
    ["/dashboard", "/home"], ["/dashboard/pillar/finance", "/home/pillar/finance"], ["/ai", "/ask"],
    ["/idp/review", "/data/review"], ["/idp/review/123", "/data/review/123"], ["/approvals", "/work/approvals"],
    ["/finance/invoices", "/business/finance/invoices"], ["/hr/employees", "/business/hr/employees"],
  ])("%s → %s", (from, to) => {
    expect(legacyRedirect(from)).toBe(to);
  });

  it("leaves v3 and look-alike paths alone", () => {
    for (const p of ["/home", "/admin/audit", "/aim", "/dashboards", "/login", "/ask"]) expect(legacyRedirect(p)).toBeNull();
  });

  it("middleware matcher covers every guarded and legacy prefix", () => {
    const src = readFileSync(new URL("../middleware.ts", import.meta.url), "utf8");
    const roots = new Set([...ROUTE_RULES.map((r) => r.prefix), ...LEGACY_ROUTES.map(([f]) => f)].map((p) => `/${p.split("/")[1]}`));
    for (const root of roots) expect(src, root).toContain(`"${root}/:path*"`);
  });
});

describe("default deny + safe callback (review M1.1)", () => {
  it("a path without a route rule is closed to every role", () => {
    expect(canAccess("/unknown", "CEO", perms("CEO"))).toBe(false);
    expect(canAccess("/homework", "CEO", perms("CEO"))).toBe(false);
  });

  it("callbackUrl stays same-origin", () => {
    const o = "https://aureon.test";
    expect(safeCallback("/home?period=2026-10", o)).toBe("/home?period=2026-10");
    for (const bad of [null, "", "//evil.com", "/\\evil.com", "https://evil.com", "home"]) {
      expect(safeCallback(bad, o)).toBe("/");
    }
  });
});

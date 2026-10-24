/** TC-M11-12 (unit) + TC-M11-13 (map) — IA v3 nav/routes per role (06 §3.2/§3.4, T-607). */
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { SNAPSHOT, type RoleCode } from "@/mocks/fixtures";
import { LEGACY_ROUTES, legacyRedirect } from "./legacy-routes";
import { ROUTE_RULES, WORK_TABS, canAccess, landingFor, safeCallback, visibleGoalsTabs, visibleNav, visibleWorkTabs } from "./permissions";

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

  it("Quản trị for DIR only with khối O (T-617F, TC-M12-18): org + positions, never users/roles/audit", () => {
    const dir = perms("DIR");
    expect(visibleNav("DIR", dir, ["O"]).map((i) => i.key)).toContain("admin");
    expect(visibleNav("DIR", dir, ["F"]).map((i) => i.key)).not.toContain("admin");
    for (const p of ["/admin", "/admin/org", "/admin/positions"]) {
      expect(canAccess(p, "DIR", dir, ["O"])).toBe(true);
      expect(canAccess(p, "DIR", dir, ["C"])).toBe(false);
      expect(canAccess(p, "DIR", dir, [])).toBe(false);
    }
    for (const p of ["/admin/users", "/admin/roles", "/admin/audit"]) expect(canAccess(p, "DIR", dir, ["O"])).toBe(false);
  });

  it.each([
    ["/admin/org", "ADM", true], ["/admin/org", "CEO", true], ["/admin/org", "MGR", false], ["/admin/org", "EMP", false],
    ["/admin/positions", "ADM", true], ["/admin/positions", "REV", false],
    ["/admin/users", "ADM", true], ["/admin/users", "CEO", true], ["/admin/users", "MGR", false],
    ["/admin/roles", "ADM", true], ["/admin/roles", "CEO", true], ["/admin/roles", "EMP", false],
  ] as const)("M1.2 admin page %s as %s → %s", (path, role, ok) => {
    expect(canAccess(path, role, perms(role))).toBe(ok);
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
    ["/data/new/PLAN_KPI_OKR", "EMP", true], ["/data/new/HR_ROSTER", "ADM", true], ["/data/imports/abc", "REV", true], ["/data/imports/abc", "ADM", true],
    ["/admin/data-capture", "ADM", true], ["/admin/data-capture", "CEO", false], ["/admin/data-capture", "DIR", false],
    ["/admin/audit", "ADM", true], ["/admin/audit", "CEO", false], ["/admin", "CEO", true],
    ["/work/projects", "EMP", true], ["/work/projects/abc", "MGR", true], ["/work/projects", "REV", false],
    ["/work/workload", "MGR", true], ["/work/workload", "DIR", true], ["/work/workload", "EMP", false], ["/work/workload", "ADM", false],
    ["/goals", "REV", false], ["/goals", "EMP", true], ["/goals/kpis/abc", "EMP", true], ["/goals/kpis/abc", "ADM", false],
    ["/goals/objectives/abc", "DIR", true], ["/goals/objectives/abc", "REV", false], ["/goals/check-ins", "EMP", true], ["/goals/check-ins", "ADM", false],
    ["/ask", "AI", false], ["/403", "EMP", true],
  ] as const)("%s as %s → %s", (path, role, ok) => {
    expect(canAccess(path, role, perms(role))).toBe(ok);
  });

  it("every human role lands on /home; the AI actor has no UI", () => {
    for (const r of ["CEO", "DIR", "MGR", "EMP", "REV", "ADM"] as const) expect(landingFor(r, perms(r))).toBe("/home");
    expect(landingFor("AI", perms("AI"))).toBe("/403");
  });
});

describe("/goals tabs per role (06 §3.4 M1.4)", () => {
  it.each(["CEO", "DIR", "MGR", "EMP"] as const)("%s sees tree + check-ins", (role) => {
    expect(visibleGoalsTabs(role, perms(role)).map((t) => t.key)).toEqual(["tree", "checkins"]);
    for (const tab of visibleGoalsTabs(role, perms(role))) expect(canAccess(tab.href, role, perms(role)), tab.href).toBe(true);
  });
  it.each(["REV", "ADM"] as const)("%s sees no goals tab", (role) => {
    expect(visibleGoalsTabs(role, perms(role))).toEqual([]);
  });
});

describe("/work tabs per role (06 §3.4 M1.3, R-DEC-48)", () => {
  it.each([
    ["CEO", ["mine", "board", "projects", "workload", "approvals"]],
    ["DIR", ["mine", "board", "projects", "workload", "approvals"]],
    ["MGR", ["mine", "board", "projects", "workload", "approvals"]],
    ["EMP", ["mine", "projects"]],
    ["REV", []],
    ["ADM", []],
  ] as const)("%s → %j", (role, keys) => {
    expect(visibleWorkTabs(role, perms(role)).map((t) => t.key)).toEqual(keys);
  });

  it("a tab is hidden when its permission is missing (MGR without platform:approve)", () => {
    const p = perms("MGR").filter((x) => x !== "platform:approve" && x !== "execution:query");
    expect(visibleWorkTabs("MGR", p).map((t) => t.key)).toEqual(["mine", "board", "projects"]);
  });

  it("every tab route is guarded by the same rule as its tab", () => {
    for (const tab of WORK_TABS) {
      for (const r of ["CEO", "DIR", "MGR", "EMP", "REV", "ADM"] as const) {
        if (tab.key === "board") continue; // query-string view of /work
        expect(canAccess(tab.href, r, perms(r)), `${tab.href} ${r}`).toBe(visibleWorkTabs(r, perms(r)).some((t) => t.key === tab.key));
      }
    }
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

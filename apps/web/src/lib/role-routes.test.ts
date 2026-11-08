/**
 * U-09 / U-42 / F15 — role × route: a screen is reachable exactly when the API behind it answers
 * that caller, so no nav item, hub card or link ends on a page of permission errors. `API` mirrors
 * the backend guards (`require_permission` / `require_pillar_permission` + the HR scope rules of
 * `hr/services/scope.py`); perms come from the real JWT matrix in the seed snapshot.
 */
import { describe, expect, it } from "vitest";
import { SNAPSHOT, type RoleCode } from "@/mocks/fixtures";
import { HUB_CARDS, activeNavHref, canAccess, canDomain, visibleHubCards, visibleNav } from "./permissions";

interface Caller { role: RoleCode; perms: readonly string[]; pillars: readonly string[] }
const has = (c: Caller, p: string) => c.perms.includes(p);
const query = (domain: string) => (c: Caller) => has(c, `${domain}:query`);
const pillarRead = (domain: string) => (c: Caller) => canDomain(c.perms, c.pillars, domain);
/** REV (review-scoped) and ADM (structure only) get 403 on every employee / hiring-plan list. */
const hrRecords = (c: Caller) => pillarRead("hr")(c) && c.role !== "REV" && c.role !== "ADM";
/** The CRM detail views: sales records in khối C, without REV's review-scoped read. */
const crmDetail = (c: Caller) => pillarRead("sales")(c) && c.role !== "REV";
/** D-07 (R-DEC-183): REV `◑r` has no general finance / sales read; MGR `◑d` has no company invoice. */
const noReviewScoped = (domain: string) => (c: Caller) => pillarRead(domain)(c) && c.role !== "REV";
const dashboard = (c: Caller) => has(c, "dashboard:read");

/** Route → the condition under which its first API call succeeds. */
const API: Readonly<Record<string, (c: Caller) => boolean>> = {
  "/business/finance": query("finance"), // EP-60 /finance/dashboard, /budgets/status, /what-if/runway
  "/business/sales": query("sales"), // EP /sales/pipeline, /sales/dashboard
  "/business/finance/invoices": (c: Caller) => noReviewScoped("finance")(c) && c.role !== "MGR",
  "/business/finance/records": noReviewScoped("finance"),
  "/business/sales/records": noReviewScoped("sales"),
  "/business/hr/employees": hrRecords,
  "/business/sales/pipeline": crmDetail,
  "/business/sales/deals/x": crmDetail,
  "/business/sales/clients/x": crmDetail,
  "/home/alerts": dashboard, // EP-15
  "/home/metrics/METRIC-FIN-01": dashboard, // EP-12
  "/data/review": (c) => has(c, "idp:approve"),
  "/goals/strategies": (c) => has(c, "execution:read") && c.role !== "EMP", // EP-STR-02; EMP keeps the own tree
};

/** Every khối a DIR can hold, plus the CEO-like "toàn khối" (`[]`). */
const callers: Caller[] = (["CEO", "MGR", "EMP", "REV", "ADM", "AI"] as const).map((role): Caller => ({ role, perms: SNAPSHOT.role_permissions[role], pillars: [] }))
  .concat(["F", "O", "C", "U", "S"].map((p) => ({ role: "DIR", perms: SNAPSHOT.role_permissions.DIR, pillars: [p] })));
const who = (c: Caller) => `${c.role}${c.pillars.length ? `/${c.pillars[0]}` : ""}`;

describe("role × route (no dead end)", () => {
  it.each(Object.keys(API))("%s opens for exactly the callers the API answers", (path) => {
    for (const c of callers.filter((x) => x.role !== "AI")) {
      expect(canAccess(path, c.role, c.perms, c.pillars), `${who(c)} ${path}`).toBe(API[path]!(c));
    }
  });

  it("the AI actor has no UI route", () => {
    const ai = callers.find((c) => c.role === "AI")!;
    for (const path of Object.keys(API)) expect(canAccess(path, ai.role, ai.perms)).toBe(false);
  });

  it("every nav item and hub card a caller sees opens for that caller", () => {
    for (const c of callers) {
      for (const item of visibleNav(c.role, c.perms, c.pillars)) expect(canAccess(item.href, c.role, c.perms, c.pillars), `${who(c)} ${item.href}`).toBe(true);
      for (const card of visibleHubCards(c.role, c.perms, c.pillars)) expect(canAccess(card.href, c.role, c.perms, c.pillars), `${who(c)} ${card.href}`).toBe(true);
    }
  });

  it.each([
    ["CEO", [], HUB_CARDS.map((c) => c.key)],
    ["MGR", [], HUB_CARDS.map((c) => c.key).filter((k) => k !== "invoices")], // no company invoice (D-07)
    ["REV", [], []], // D-07: finance / sales only inside an assigned review; no HR records
    ["EMP", [], ["employees"]], // own profile only
    ["ADM", [], []],
    ["DIR", ["F"], ["finance", "sales", "invoices", "financeRecords"]],
    ["DIR", ["C"], ["finance", "sales", "salesRecords"]],
    ["DIR", ["O"], ["finance", "sales", "employees", "hrRecords"]],
  ] as const)("hub cards of %s %j", (role, pillars, keys) => {
    expect(visibleHubCards(role, SNAPSHOT.role_permissions[role], pillars).map((c) => c.key)).toEqual(keys);
  });

  it("a nav item needs the permission of its API, not just the role", () => {
    const rev = SNAPSHOT.role_permissions.REV.filter((p) => p !== "idp:approve");
    expect(visibleNav("REV", rev).map((i) => i.key)).not.toContain("review");
  });
});

describe("review queue entry (U-01)", () => {
  const nav = (r: RoleCode) => visibleNav(r, SNAPSHOT.role_permissions[r]);

  it("appears for review duty only", () => {
    for (const r of ["REV", "MGR", "DIR"] as const) expect(nav(r).map((i) => i.key)).toContain("review");
    for (const r of ["CEO", "EMP", "ADM"] as const) expect(nav(r).map((i) => i.key)).not.toContain("review"); // no idp:approve
  });

  it("only the most specific item is current", () => {
    const items = nav("REV");
    expect(activeNavHref("/data/review", items)).toBe("/data/review");
    expect(activeNavHref("/data/review/abc", items)).toBe("/data/review");
    expect(activeNavHref("/data", items)).toBe("/data");
    expect(activeNavHref("/data/new/X", items)).toBe("/data");
    expect(activeNavHref("/homework", items)).toBeUndefined();
  });
});

/** TC-M6-03 (unit) — khối-aware access, permission-aware Knowledge tabs, error semantics (M6 role QA). */
import { describe, expect, it } from "vitest";
import { SNAPSHOT, type RoleCode } from "@/mocks/fixtures";
import { canReadOrg } from "@/features/work/WorkShell";
import { goalCaps } from "@/features/goals/GoalsShell";
import { visibleKnowledgeTabs } from "@/features/knowledge/tabs";
import { ApiError } from "./api-client";
import { errorKind, errorText } from "./error-text";
import { canAccess, canDomain, inPillar } from "./permissions";

const perms = (r: RoleCode) => SNAPSHOT.role_permissions[r];
const user = (role: RoleCode, scopePillars: string[] = []) => ({ id: "u", role, permissions: perms(role), scopePillars });

describe("khối isolation mirrors `require_pillar_permission` (R-DEC-12a)", () => {
  it("inPillar / canDomain", () => {
    expect(inPillar("hr", [])).toBe(true); // CEO / DIR toàn khối
    expect(inPillar("hr", ["F"])).toBe(false);
    expect(inPillar("hr", ["O"])).toBe(true);
    expect(inPillar("execution", ["F"])).toBe(true); // cross-pillar domain
    expect(canDomain(perms("DIR"), ["F"], "finance")).toBe(true);
    expect(canDomain(perms("DIR"), ["C"], "hr")).toBe(false);
  });

  it("/business/hr and invoices follow the khối; cross-khối overviews stay open", () => {
    const can = (path: string, role: RoleCode, p: string[] = []) => canAccess(path, role, perms(role), p);
    expect(can("/business/hr/employees", "DIR", ["C"])).toBe(false); // Sales-DIR → /403, not a 403 page
    expect(can("/business/hr/employees", "DIR", ["O"])).toBe(true);
    expect(can("/business/hr/employees", "CEO")).toBe(true);
    expect(can("/business/finance/invoices", "DIR", ["C"])).toBe(false);
    expect(can("/business/finance/invoices", "DIR", ["F"])).toBe(true);
    expect(can("/business/finance", "DIR", ["C"])).toBe(true); // /finance/dashboard = finance:query
    expect(can("/business/sales", "DIR", ["F"])).toBe(true); // /sales/pipeline = sales:query
  });

  it("Work pickers do not call /org/tree outside khối O; Goals department filter likewise", () => {
    expect(canReadOrg(user("DIR", ["F"]))).toBe(false); // CFO: /org/tree → 403 before M6
    expect(canReadOrg(user("DIR", ["O"]))).toBe(true);
    expect(canReadOrg(user("CEO"))).toBe(true);
    expect(canReadOrg(user("REV"))).toBe(false);
    expect(canReadOrg(user("EMP"))).toBe(false);
    expect(goalCaps(user("DIR", ["C"])).canFilterDepartment).toBe(false); // /hr/departments → 403
    expect(goalCaps(user("DIR", ["O"])).canFilterDepartment).toBe(true);
    expect(goalCaps(user("CEO")).canFilterDepartment).toBe(true);
  });
});

describe("Knowledge tabs by permission (SCR-49)", () => {
  it.each([
    ["CEO", ["decisions", "documents", "reports"]],
    ["DIR", ["decisions", "documents", "reports"]],
    ["REV", ["documents"]], // no execution:read / dashboard:read → those tabs 403'd before M6
  ] as const)("%s", (role, tabs) => {
    expect(visibleKnowledgeTabs(perms(role))).toEqual(tabs);
  });
});

describe("error semantics: permission ≠ not found ≠ system", () => {
  const t = Object.assign((k: string) => k, { has: (k: string) => ["errors.FORBIDDEN_ROLE", "errors.FORBIDDEN_SCOPE"].includes(k) });
  it.each([
    [new ApiError(403, "FORBIDDEN_ROLE", "x"), "forbidden", "errors.FORBIDDEN_ROLE"],
    [new ApiError(403, "HTTP_403", "x"), "forbidden", "errors.forbiddenData"],
    [new ApiError(404, "NOT_FOUND", "x"), "notFound", "errors.notFoundData"],
    [new ApiError(500, "INTERNAL_ERROR", "x"), "system", "errors.generic"],
    [new TypeError("Failed to fetch"), "network", "errors.network"],
  ])("%s", (e, kind, key) => {
    expect(errorKind(e)).toBe(kind);
    expect(errorText(t, e)).toBe(key);
  });
});

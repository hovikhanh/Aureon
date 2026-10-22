import { describe, expect, it } from "vitest";
import { canAccess, landingFor, visibleNav } from "./permissions";

const CEO = ["dashboard:read", "ai:query", "platform:approve", "finance:read", "idp:read"];
const REVIEWER = ["ai:query", "finance:read", "idp:approve", "idp:read"];
const HR = ["dashboard:read", "hr:read", "ai:query", "idp:approve"];
const ADMIN = ["ai:query", "ai:admin", "platform:read", "platform:admin"];

describe("permissions", () => {
  it("filters nav per role", () => {
    expect(visibleNav(CEO).map((i) => i.key)).toEqual(["dashboard", "ai", "approvals"]);
    expect(visibleNav(REVIEWER).map((i) => i.key)).toEqual(["idp", "ai"]);
  });
  it("guards routes", () => {
    expect(canAccess("/dashboard/pillar/finance", CEO)).toBe(true);
    expect(canAccess("/idp/review", CEO)).toBe(false);
    expect(canAccess("/dashboard", REVIEWER)).toBe(false);
    expect(canAccess("/finance/invoices", REVIEWER)).toBe(true);
  });
  it("lands per role", () => {
    expect(landingFor("CEO", CEO)).toBe("/dashboard");
    expect(landingFor("REVIEWER", REVIEWER)).toBe("/idp/review");
    expect(landingFor("EMPLOYEE", ["ai:query"])).toBe("/ai");
    expect(landingFor("ADMIN", ADMIN)).toBe("/admin/audit");
  });
  it("HR sees employees, ADMIN sees audit (T-516)", () => {
    expect(visibleNav(HR).map((i) => i.key)).toContain("employees");
    expect(canAccess("/hr/employees", HR)).toBe(true);
    expect(canAccess("/admin/audit", HR)).toBe(false);
    expect(visibleNav(ADMIN).map((i) => i.key)).toEqual(["ai", "audit"]);
    expect(canAccess("/admin/audit", ADMIN)).toBe(true);
    expect(canAccess("/hr/employees", ADMIN)).toBe(false);
  });
});

import { describe, expect, it } from "vitest";
import { canAccess, landingFor, visibleNav } from "./permissions";

const CEO = ["dashboard:read", "ai:query", "platform:approve", "finance:read", "idp:read"];
const REVIEWER = ["ai:query", "finance:read", "idp:approve", "idp:read"];

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
  });
});

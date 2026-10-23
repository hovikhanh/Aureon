import { describe, expect, it } from "vitest";
import { DEMO_ACCOUNTS, demoTestId } from "./demo-accounts";
import { MOCK_USERS } from "@/mocks/fixtures";
import vi from "../../messages/vi.json";
import en from "../../messages/en.json";

/** T-610b: the quick-login list must stay in sync with the seeded demo users (08 §2.1). */
describe("DEMO_ACCOUNTS", () => {
  it("covers every seeded human account exactly once", () => {
    const seeded = MOCK_USERS.map((u) => u.email).sort();
    expect(DEMO_ACCOUNTS.map((a) => a.email).sort()).toEqual(seeded);
  });

  it("carries the seeded role and khối of each account", () => {
    for (const a of DEMO_ACCOUNTS) {
      const user = MOCK_USERS.find((u) => u.email === a.email);
      expect(user, a.email).toBeDefined();
      expect(user?.role, a.email).toBe(a.role);
      expect([...(user?.scope_pillars ?? [])].sort(), a.email).toEqual(a.pillar ? [a.pillar] : []);
    }
  });

  it("has a vi + en label for every account", () => {
    for (const a of DEMO_ACCOUNTS) {
      expect(vi.demoAccount, a.labelKey).toHaveProperty(a.labelKey);
      expect(en.demoAccount, a.labelKey).toHaveProperty(a.labelKey);
    }
  });

  it("derives a distinct test id per account", () => {
    const ids = DEMO_ACCOUNTS.map((a) => demoTestId(a.email));
    expect(new Set(ids).size).toBe(DEMO_ACCOUNTS.length);
    expect(demoTestId("ceo@abc.demo")).toBe("demo-login-ceo");
  });
});

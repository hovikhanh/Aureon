/** TC-M11-10 (T-604, R-DEC-25) — API_MODE=mock refused in production; mock login = 7-role claims. */
import { describe, expect, it } from "vitest";
import { resolveApiMode } from "@/lib/server-env";
import { decodeMockToken, mockAuthorize } from "./auth";
import { MOCK_USERS, SNAPSHOT } from "./fixtures";

describe("API_MODE guard", () => {
  it("defaults to real and accepts mock outside production", () => {
    expect(resolveApiMode({})).toBe("real");
    expect(resolveApiMode({ API_MODE: "mock", NODE_ENV: "development" })).toBe("mock");
    expect(resolveApiMode({ API_MODE: "mock", NODE_ENV: "test" })).toBe("mock");
  });

  it("refuses mock when NODE_ENV=production and rejects unknown modes", () => {
    expect(() => resolveApiMode({ API_MODE: "mock", NODE_ENV: "production" })).toThrow(/forbidden/);
    expect(() => resolveApiMode({ API_MODE: " MOCK ", NODE_ENV: "production" })).toThrow(/forbidden/);
    expect(resolveApiMode({ API_MODE: "real", NODE_ENV: "production" })).toBe("real");
    expect(() => resolveApiMode({ API_MODE: "msw" })).toThrow(/real" or "mock/);
  });
});

describe("mock authorize", () => {
  it("covers the 6 human roles + 10 accounts; the AI actor cannot log in", () => {
    expect(new Set(MOCK_USERS.map((u) => u.role))).toEqual(new Set(["CEO", "DIR", "MGR", "EMP", "REV", "ADM"]));
    expect(MOCK_USERS).toHaveLength(10);
    expect(() => mockAuthorize("ai-agent@abc.demo", "x", false, {})).toThrow("INVALID_CREDENTIALS");
    expect(Object.keys(SNAPSHOT.role_permissions).sort()).toEqual(["ADM", "AI", "CEO", "DIR", "EMP", "MGR", "REV"]);
  });

  it.each(MOCK_USERS.map((u) => [u.email, u] as const))("%s gets the real-JWT claim set", (email, u) => {
    const login = mockAuthorize(email, "any-Pass", false, {});
    const claims = decodeMockToken(login.accessToken)!;
    expect(claims.role).toBe(u.role);
    expect(login.role).toBe(u.role);
    expect(claims.permissions).toEqual(SNAPSHOT.role_permissions[u.role]);
    expect(login.permissions).toEqual(claims.permissions);
    expect(claims.scope_pillars).toEqual([...u.scope_pillars].sort());
    expect(claims.email).toBe(email);
    expect(Object.keys(claims).sort()).toEqual(["department_id", "email", "employee_id", "name", "permissions", "role", "scope_pillars", "sub"]);
  });

  it("scope pillars of the 4 DIR accounts follow 08 §2.1", () => {
    const dir = Object.fromEntries(MOCK_USERS.filter((u) => u.role === "DIR").map((u) => [u.email, u.scope_pillars]));
    expect(dir).toEqual({ "sales@abc.demo": ["C"], "cfo@abc.demo": ["F"], "hr@abc.demo": ["O"], "cpo@abc.demo": ["U"] });
  });

  it("enforces MOCK_LOGIN_PASSWORD when set, rejects unknown users and empty passwords", () => {
    const env = { MOCK_LOGIN_PASSWORD: "s3cret" };
    expect(() => mockAuthorize("ceo@abc.demo", "wrong", false, env)).toThrow("INVALID_CREDENTIALS");
    expect(mockAuthorize("CEO@abc.demo ", "s3cret", false, env).role).toBe("CEO");
    expect(mockAuthorize("ceo@abc.demo", "", true, env).role).toBe("CEO"); // demo quick-login
    expect(() => mockAuthorize("ceo@abc.demo", "", false, {})).toThrow("INVALID_CREDENTIALS");
    expect(() => mockAuthorize("ghost@abc.demo", "x", false, {})).toThrow("INVALID_CREDENTIALS");
  });

  it("mock tokens are not JWTs and tampered tokens decode to null", () => {
    const t = mockAuthorize("employee@abc.demo", "p", false, {}).accessToken;
    expect(t.split(".")).toHaveLength(2);
    expect(decodeMockToken("eyJhbGciOiJSUzI1NiJ9.e30.sig")).toBeNull();
    expect(decodeMockToken("mock.not-json")).toBeNull();
    expect(decodeMockToken(undefined)).toBeNull();
  });
});

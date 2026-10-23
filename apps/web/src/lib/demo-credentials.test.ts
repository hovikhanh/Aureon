import { describe, expect, it } from "vitest";
import { isDemoAutofillEnabled, resolveDemoCredentials } from "./demo-credentials";
import { DEMO_ACCOUNTS } from "./demo-accounts";

/** T-610c / TC-M11-17 (R-DEC-28): demo-credentials Route Handler gates + whitelist. */
const ON = { DEMO_MODE: "true", DEMO_LOGIN_AUTOFILL: "true", DEMO_CEO_PASSWORD: "ceo-dev-pass", DEMO_PASSWORD: "shared-dev-pass" };

describe("resolveDemoCredentials", () => {
  it("returns the demo password when DEMO_MODE + DEMO_LOGIN_AUTOFILL are on", () => {
    expect(resolveDemoCredentials("ceo@abc.demo", ON)).toEqual({
      status: 200,
      body: { data: { email: "ceo@abc.demo", password: "ceo-dev-pass" } },
    });
    expect(resolveDemoCredentials(" CEO@abc.demo ", ON).status).toBe(200);
  });

  it("answers all 10 demo accounts (DEMO_PASSWORD fallback)", () => {
    for (const a of DEMO_ACCOUNTS) expect(resolveDemoCredentials(a.email, ON).status, a.email).toBe(200);
  });

  it("is 404 NOT_FOUND when DEMO_MODE is off", () => {
    const r = resolveDemoCredentials("ceo@abc.demo", { ...ON, DEMO_MODE: "false" });
    expect(r).toMatchObject({ status: 404, body: { error: { code: "NOT_FOUND" } } });
    expect(JSON.stringify(r)).not.toContain("ceo-dev-pass");
  });

  it("is 404 when the server-only autofill flag is off (production default)", () => {
    expect(resolveDemoCredentials("ceo@abc.demo", { ...ON, DEMO_LOGIN_AUTOFILL: undefined }).status).toBe(404);
    expect(resolveDemoCredentials("ceo@abc.demo", { ...ON, NODE_ENV: "production", DEMO_LOGIN_AUTOFILL: "false" }).status).toBe(404);
    expect(isDemoAutofillEnabled({ DEMO_LOGIN_AUTOFILL: "true" })).toBe(false);
  });

  it("is 404 for an e-mail outside DEMO_ACCOUNTS, or a non-string e-mail", () => {
    for (const e of ["ai-agent@abc.demo", "someone@example.com", "", 42, undefined, null]) {
      const r = resolveDemoCredentials(e, ON);
      expect(r.status, String(e)).toBe(404);
      expect(JSON.stringify(r)).not.toContain("shared-dev-pass");
    }
  });

  it("is 404 when no password is configured", () => {
    expect(resolveDemoCredentials("ceo@abc.demo", { DEMO_MODE: "true", DEMO_LOGIN_AUTOFILL: "true" }).status).toBe(404);
  });

  it("serves MOCK_LOGIN_PASSWORD in API_MODE=mock", () => {
    const env = { DEMO_MODE: "true", DEMO_LOGIN_AUTOFILL: "true", API_MODE: "mock", MOCK_LOGIN_PASSWORD: "mock-pass" };
    expect(resolveDemoCredentials("cfo@abc.demo", env)).toMatchObject({ status: 200, body: { data: { password: "mock-pass" } } });
  });
});

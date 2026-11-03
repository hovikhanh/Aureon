import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

/**
 * T-1021 / TC-M4-10 — NextAuth wiring (`lib/auth.ts`) was at 0% measured coverage although it
 * is the only place the backend RS256 access token and the rotating refresh token are handled
 * (CLAUDE §5.8). These tests pin the security-relevant behaviour: EP-02 error codes surface
 * unchanged, a refused EP-06 refresh marks the session dead instead of keeping stale tokens,
 * and the browser-visible session never carries a token.
 */
const ENV = {
  API_URL: "http://api.test",
  API_MODE: "real",
  NEXTAUTH_SECRET: "x".repeat(32),
};

type Json = { ok: boolean; body: unknown };

function stubFetch(...responses: Json[]): ReturnType<typeof vi.fn> {
  const fn = vi.fn(async () => {
    const next = responses.shift() ?? { ok: false, body: null };
    return {
      ok: next.ok,
      json: async () => next.body,
    } as Response;
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}

const tokenOut = (suffix: string) => ({
  data: {
    access_token: `access-${suffix}`,
    refresh_token: `refresh-${suffix}`,
    expires_in: 900,
    user: {
      id: "u-1",
      email: "ceo@abc.demo",
      full_name: "CEO",
      role_code: "CEO",
      permissions: ["dashboard:read", "ai:query"],
    },
  },
});

async function load() {
  vi.resetModules();
  for (const [k, v] of Object.entries(ENV)) vi.stubEnv(k, v);
  return import("./auth");
}

/** The Credentials provider's `authorize`, dug out of the options object. */
function authorizeOf(options: { providers: unknown[] }) {
  const provider = options.providers[0] as {
    options?: { authorize?: unknown };
    authorize?: unknown;
  };
  const fn = provider.options?.authorize ?? provider.authorize;
  return fn as (creds: Record<string, string> | undefined) => Promise<Record<string, unknown>>;
}

beforeEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("refreshTokens (EP-06 rotation)", () => {
  it("replaces both tokens, role and permissions on success and clears a previous error", async () => {
    const { refreshTokens } = await load();
    stubFetch({ ok: true, body: tokenOut("2") });

    const next = await refreshTokens({
      refreshToken: "refresh-1",
      accessToken: "access-1",
      expiresAt: 0,
      error: "RefreshFailed",
    } as never);

    expect(next.accessToken).toBe("access-2");
    expect(next.refreshToken).toBe("refresh-2");
    expect(next.role).toBe("CEO");
    expect(next.permissions).toEqual(["dashboard:read", "ai:query"]);
    expect(next.expiresAt).toBeGreaterThan(Date.now());
    expect(next.error).toBeUndefined();
  });

  it("marks the session dead (never keeps the old tokens) when the refresh is refused", async () => {
    const { refreshTokens } = await load();
    stubFetch({ ok: false, body: { error: { code: "UNAUTHORIZED" } } });

    const next = await refreshTokens({ refreshToken: "reused", expiresAt: 0 } as never);

    expect(next.error).toBe("RefreshFailed");
  });

  it("does not throw when the API is unreachable — it reports RefreshFailed", async () => {
    const { refreshTokens } = await load();
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("ECONNREFUSED");
      }),
    );

    await expect(refreshTokens({ refreshToken: "r", expiresAt: 0 } as never)).resolves.toMatchObject(
      { error: "RefreshFailed" },
    );
  });
});

describe("authorize (EP-02 login)", () => {
  it("returns the user with both tokens and an absolute expiry", async () => {
    const { authOptions } = await load();
    const fetchMock = stubFetch({ ok: true, body: tokenOut("1") });

    const user = await authorizeOf(authOptions)({ email: " ceo@abc.demo ", password: "pw" });

    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.test/api/v1/auth/login",
      expect.objectContaining({ method: "POST", cache: "no-store" }),
    );
    expect(user).toMatchObject({
      id: "u-1",
      role: "CEO",
      accessToken: "access-1",
      refreshToken: "refresh-1",
    });
    expect(user.expiresAt as number).toBeGreaterThan(Date.now());
  });

  it("surfaces the backend error code unchanged (the login page maps it to i18n)", async () => {
    const { authOptions } = await load();
    stubFetch({ ok: false, body: { error: { code: "ACCOUNT_LOCKED" } } });

    await expect(
      authorizeOf(authOptions)({ email: "ceo@abc.demo", password: "pw" }),
    ).rejects.toThrow("ACCOUNT_LOCKED");
  });

  it("falls back to INTERNAL_ERROR for a body without an error code", async () => {
    const { authOptions } = await load();
    stubFetch({ ok: false, body: null });

    await expect(
      authorizeOf(authOptions)({ email: "ceo@abc.demo", password: "pw" }),
    ).rejects.toThrow("INTERNAL_ERROR");
  });

  it("reports DEPENDENCY_UNAVAILABLE when the API cannot be reached", async () => {
    const { authOptions } = await load();
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("ECONNREFUSED");
      }),
    );

    await expect(
      authorizeOf(authOptions)({ email: "ceo@abc.demo", password: "pw" }),
    ).rejects.toThrow("DEPENDENCY_UNAVAILABLE");
  });

  it("refuses an empty e-mail or password without calling the API", async () => {
    const { authOptions } = await load();
    const fetchMock = stubFetch({ ok: true, body: tokenOut("1") });

    await expect(authorizeOf(authOptions)({ email: "  ", password: "pw" })).rejects.toThrow(
      "INVALID_CREDENTIALS",
    );
    await expect(
      authorizeOf(authOptions)({ email: "ceo@abc.demo", password: "" }),
    ).rejects.toThrow("INVALID_CREDENTIALS");
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe("callbacks", () => {
  it("jwt copies the tokens in on sign-in and passes the token through afterwards", async () => {
    const { authOptions } = await load();
    const jwt = authOptions.callbacks!.jwt!;
    const user = {
      id: "u-1",
      name: "CEO",
      email: "ceo@abc.demo",
      role: "CEO",
      permissions: ["ai:query"],
      scopePillars: ["F"],
      accessToken: "a",
      refreshToken: "r",
      expiresAt: 42,
    };

    const signedIn = await jwt({ token: {}, user } as never);
    expect(signedIn).toMatchObject({ uid: "u-1", accessToken: "a", refreshToken: "r" });

    const later = await jwt({ token: { uid: "u-1", accessToken: "a" } } as never);
    expect(later).toEqual({ uid: "u-1", accessToken: "a" });
  });

  it("session exposes identity + permissions but never a token (CLAUDE §5.8)", async () => {
    const { authOptions } = await load();
    const session = await authOptions.callbacks!.session!({
      session: {} as never,
      token: {
        uid: "u-1",
        email: "ceo@abc.demo",
        name: "CEO",
        role: "CEO",
        permissions: ["ai:query"],
        accessToken: "access-secret",
        refreshToken: "refresh-secret",
      } as never,
    } as never);

    expect(session.user).toEqual({
      id: "u-1",
      email: "ceo@abc.demo",
      name: "CEO",
      role: "CEO",
      permissions: ["ai:query"],
      scopePillars: [],
    });
    expect(JSON.stringify(session)).not.toContain("secret");
  });

  it("session carries the error flag so the UI can force a re-login", async () => {
    const { authOptions } = await load();
    // the callback's declared return is the `Session | DefaultSession` union; the augmented
    // `error` field (types/next-auth.d.ts) lives on `Session`, so narrow before asserting
    const session = (await authOptions.callbacks!.session!({
      session: {} as never,
      token: { uid: "u-1", role: "CEO", permissions: [], error: "RefreshFailed" } as never,
    } as never)) as { error?: string };

    expect(session.error).toBe("RefreshFailed");
  });
});

// @vitest-environment node
import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiClientError, apiFetch, getApiBaseUrl, parseEnvelope } from "./api-client";

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("api-client envelope parsing (10 §1.2)", () => {
  it("returns the success envelope", () => {
    expect(parseEnvelope(200, { data: { ok: true }, meta: { page: 1 } })).toEqual({
      data: { ok: true },
      meta: { page: 1 },
    });
  });

  it("throws ApiClientError for the error envelope", () => {
    const err = (() => {
      try {
        parseEnvelope(403, { error: { code: "FORBIDDEN_ROLE", message: "no", details: { a: 1 } } });
      } catch (e) {
        return e;
      }
    })();
    expect(err).toBeInstanceOf(ApiClientError);
    expect(err).toMatchObject({ code: "FORBIDDEN_ROLE", status: 403, details: { a: 1 } });
  });

  it("throws for malformed bodies", () => {
    expect(() => parseEnvelope(200, null)).toThrow(ApiClientError);
    expect(() => parseEnvelope(502, "oops")).toThrowError(/HTTP 502/);
  });
});

describe("api-client base URL", () => {
  it("uses API_BASE_URL on the server and strips trailing slashes", () => {
    vi.stubEnv("API_BASE_URL", "http://localhost:4000/api/v1/");
    expect(getApiBaseUrl()).toBe("http://localhost:4000/api/v1");
  });

  it("falls back to same-origin /api/v1", () => {
    vi.stubEnv("API_BASE_URL", "");
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "");
    expect(getApiBaseUrl()).toBe("/api/v1");
  });

  it("apiFetch joins the path, sends JSON and disables caching", async () => {
    vi.stubEnv("API_BASE_URL", "http://api.test/api/v1");
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ data: 1 }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    await expect(apiFetch<number>("/health", { method: "POST", json: { x: 1 } })).resolves.toEqual({ data: 1 });
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.test/api/v1/health",
      expect.objectContaining({ cache: "no-store", method: "POST", body: '{"x":1}' }),
    );
  });
});

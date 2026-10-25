/** TC-M16-21 (unit) — SCR-65 filters (T-647F). */
import { describe, expect, it } from "vitest";
import { defaultRange, rangeQuery, shortHash, usd4 } from "./log-logic";

describe("SCR-65 helpers", () => {
  it("default period = last 7 days", () => {
    expect(defaultRange(new Date("2026-10-20T10:00:00Z"))).toEqual({ from: "2026-10-13", to: "2026-10-20" });
  });
  it("request_id + inclusive UTC bounds", () => {
    expect(rangeQuery({ from: "2026-10-13", to: "2026-10-20", requestId: "req-1" })).toEqual({ from: "2026-10-13T00:00:00Z", to: "2026-10-20T23:59:59Z", request_id: "req-1" });
    expect(rangeQuery({ from: "", to: "", requestId: "" })).toEqual({});
  });
  it("cost 4 dp, short hash", () => {
    expect(usd4(0.01234)).toBe("$0.0123");
    expect(shortHash("abcdef0123456789")).toBe("abcdef01…");
    expect(shortHash(null)).toBe("—");
  });
});

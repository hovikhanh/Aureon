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

describe("M5 telemetry helpers (R-DEC-155)", () => {
  it("isUnpriced: cloud + tokens + $0 only; local Ollama and token-less failures are not", async () => {
    const { isUnpriced } = await import("./log-logic");
    expect(isUnpriced({ provider: "omniroute", cost_usd: 0, tokens_in: 900, tokens_out: 40 })).toBe(true);
    expect(isUnpriced({ provider: "omniroute", cost_usd: 0.0012, tokens_in: 900, tokens_out: 40 })).toBe(false);
    expect(isUnpriced({ provider: "ollama", cost_usd: 0, tokens_in: 900, tokens_out: 40 })).toBe(false);
    expect(isUnpriced({ provider: "omniroute", cost_usd: 0, tokens_in: 0, tokens_out: 0 })).toBe(false);
  });

  it("modelCallQuery keeps the range and adds only the filters that are set", async () => {
    const { modelCallQuery, EMPTY_MODEL_FILTER } = await import("./log-logic");
    const base = { from: "2026-11-01T00:00:00Z", to: "2026-11-03T23:59:59Z" };
    expect(modelCallQuery(base, EMPTY_MODEL_FILTER)).toEqual(base);
    expect(modelCallQuery(base, { provider: "ollama", model: "  qwen2.5:7b-instruct ", status: "timeout" })).toEqual({
      ...base, provider: "ollama", model: "qwen2.5:7b-instruct", status: "timeout",
    });
  });

  it("usageTotals sums rows and weights the error rate by calls", async () => {
    const { usageTotals } = await import("./log-logic");
    const t = usageTotals([
      { calls: 3, tokens_in: 3000, tokens_out: 120, cost_usd: 0, error_rate: 1 / 3, unpriced_calls: 2 },
      { calls: 1, tokens_in: 1400, tokens_out: 60, cost_usd: 0, error_rate: 0, unpriced_calls: 0 },
    ]);
    expect(t).toEqual({ calls: 4, tokensIn: 4400, tokensOut: 180, costUsd: 0, errors: 1, errorRate: 0.25, unpriced: 2 });
    expect(usageTotals([]).errorRate).toBe(0);
  });
});

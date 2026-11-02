import { describe, expect, it } from "vitest";
import { fmtPct, scoreBand, sortRunsByFinished } from "./logic";

describe("scoreBand", () => {
  it("maps to good/warn/bad at the 90 and 70 thresholds", () => {
    expect(scoreBand(95)).toBe("good");
    expect(scoreBand(90)).toBe("good");
    expect(scoreBand(89.9)).toBe("warn");
    expect(scoreBand(70)).toBe("warn");
    expect(scoreBand(69.9)).toBe("bad");
    expect(scoreBand(0)).toBe("bad");
  });
});

describe("fmtPct", () => {
  it("formats one decimal and dashes null/NaN", () => {
    expect(fmtPct(95.833)).toBe("95.8%");
    expect(fmtPct(100)).toBe("100.0%");
    expect(fmtPct(null)).toBe("—");
    expect(fmtPct(undefined)).toBe("—");
    expect(fmtPct(NaN)).toBe("—");
  });
});

describe("sortRunsByFinished", () => {
  it("sorts latest finished first and puts null finishes last", () => {
    const runs = [
      { id: "a", finished_at: "2026-01-01T00:00:00Z" },
      { id: "b", finished_at: "2026-03-01T00:00:00Z" },
      { id: "c", finished_at: null },
    ];
    expect(sortRunsByFinished(runs).map((r) => r.id)).toEqual(["b", "a", "c"]);
  });

  it("does not mutate the input", () => {
    const runs = [
      { id: "a", finished_at: "2026-01-01T00:00:00Z" },
      { id: "b", finished_at: "2026-03-01T00:00:00Z" },
    ];
    sortRunsByFinished(runs);
    expect(runs.map((r) => r.id)).toEqual(["a", "b"]);
  });
});

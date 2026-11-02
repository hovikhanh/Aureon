import { describe, expect, it } from "vitest";
import { chartSeries, hasTrend, thresholdLines, totalRecords } from "./metric-detail";
import type { MetricDetail, TrendPoint } from "./types";

const trend: TrendPoint[] = [
  { period_key: "2026-10", value: 86.4 },
  { period_key: "2026-09", value: 80.0 },
  { period_key: "2026-08", value: null },
];

describe("metric-detail helpers", () => {
  it("chartSeries reverses newest-first API order to oldest→newest", () => {
    const s = chartSeries(trend);
    expect(s.map((p) => p.period_key)).toEqual(["2026-08", "2026-09", "2026-10"]);
    expect(s[2]?.value).toBe(86.4);
  });

  it("chartSeries does not mutate the input", () => {
    const copy = [...trend];
    chartSeries(trend);
    expect(trend).toEqual(copy);
  });

  it("hasTrend needs ≥ 2 non-null points", () => {
    expect(hasTrend(trend)).toBe(true);
    expect(hasTrend([{ period_key: "2026-10", value: 1 }, { period_key: "2026-09", value: null }])).toBe(false);
    expect(hasTrend([])).toBe(false);
  });

  it("thresholdLines carries direction and both bands", () => {
    const d = { thresholds: { warning: 60, critical: 40 }, direction: "down" } as Pick<
      MetricDetail,
      "thresholds" | "direction"
    >;
    expect(thresholdLines(d)).toEqual({ warning: 60, critical: 40, direction: "down" });
  });

  it("totalRecords sums breakdown record_count", () => {
    const d = { breakdown: [{ key: "a", label: "A", value: 1, record_count: 3 }, { key: "b", label: "B", value: 2, record_count: 5 }] } as Pick<
      MetricDetail,
      "breakdown"
    >;
    expect(totalRecords(d)).toBe(8);
  });
});

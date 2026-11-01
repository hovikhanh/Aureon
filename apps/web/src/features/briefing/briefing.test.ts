import { describe, expect, it } from "vitest";
import type { Api } from "@aureon/shared-types";
import { BRIEFING_BLOCK_ORDER, briefingBlocks, isOpened, openedAt, staleCount } from "./briefing";

function briefing(p: Partial<Api.BriefingOut> = {}): Api.BriefingOut {
  return {
    id: "b1",
    briefing_date: "2026-11-02",
    generated_at: "2026-11-02T00:30:00Z",
    summary_line: "Công ty đang đạt 82% mục tiêu quý.",
    dashboard: {
      summary_line: "Công ty đang đạt 82% mục tiêu quý.",
      tiles: [{ metric_code: "FIN-REV" }],
      sei: { metric_code: "SEI" },
      decisions_waiting: { count: 2, items: [] },
      open_risks: { count: 1, items: [] },
      ai_done: { count: 3, items: [] },
      generated_at: "2026-11-02T00:30:00Z",
    } as unknown as Record<string, unknown>,
    recommendations: [{ id: "i1" } as Api.InsightOut],
    calendar_today: [{ id: "c1", title: "Họp HĐQT", starts_at: "2026-11-02T02:00:00Z" }],
    stale_metric_codes: ["FIN-GM", "OPS-SLA"],
    opened_at: null,
    status: "generated",
    ...p,
  };
}

describe("briefingBlocks", () => {
  it("returns every block in the fixed one-page order", () => {
    const keys = briefingBlocks(briefing()).map((b) => b.key);
    expect(keys).toEqual([...BRIEFING_BLOCK_ORDER]);
  });

  it("flags presence from the briefing content", () => {
    const by = Object.fromEntries(briefingBlocks(briefing()).map((b) => [b.key, b.present]));
    expect(by.summary).toBe(true);
    expect(by.stale).toBe(true);
    expect(by.metrics).toBe(true);
    expect(by.sei).toBe(true);
    expect(by.recommendations).toBe(true);
    expect(by.calendar).toBe(true);
  });

  it("marks empty blocks absent", () => {
    const b = briefing({
      summary_line: "",
      stale_metric_codes: [],
      recommendations: [],
      calendar_today: [],
      dashboard: {} as unknown as Record<string, unknown>,
    });
    const by = Object.fromEntries(briefingBlocks(b).map((x) => [x.key, x.present]));
    expect(by.summary).toBe(false);
    expect(by.stale).toBe(false);
    expect(by.metrics).toBe(false);
    expect(by.sei).toBe(false);
    expect(by.recommendations).toBe(false);
    expect(by.calendar).toBe(false);
  });
});

describe("staleCount", () => {
  it("counts the stale metric codes", () => {
    expect(staleCount(briefing())).toBe(2);
    expect(staleCount(briefing({ stale_metric_codes: [] }))).toBe(0);
    expect(staleCount(briefing({ stale_metric_codes: undefined }))).toBe(0);
  });
});

describe("isOpened / openedAt", () => {
  it("is false for a freshly generated briefing", () => {
    expect(isOpened(briefing())).toBe(false);
    expect(openedAt(briefing())).toBeNull();
  });
  it("is true when the status flipped to opened", () => {
    expect(isOpened(briefing({ status: "opened" }))).toBe(true);
  });
  it("is true when an opened_at stamp is present", () => {
    const b = briefing({ status: "generated", opened_at: "2026-11-02T01:00:00Z" });
    expect(isOpened(b)).toBe(true);
    expect(openedAt(b)).toBe("2026-11-02T01:00:00Z");
  });
});

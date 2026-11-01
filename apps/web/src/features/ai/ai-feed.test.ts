import { describe, expect, it } from "vitest";
import { feedActions, remainingLabel, remainingMs, undoable, type FeedAction } from "./ai-feed";

const NOW = Date.parse("2026-11-01T12:00:00Z");

function act(p: Partial<FeedAction>): FeedAction {
  return {
    id: "a", action_name: "ACT-execute_recommendation", autonomy_level: "L3",
    status: "executed", executed_at: "2026-11-01T11:00:00Z",
    undo_deadline: "2026-11-02T11:00:00Z", can_undo: true, ...p,
  };
}

describe("feedActions", () => {
  it("keeps only executed L3 actions, newest first", () => {
    const rows = [
      act({ id: "old", executed_at: "2026-11-01T08:00:00Z" }),
      act({ id: "new", executed_at: "2026-11-01T10:00:00Z" }),
      act({ id: "proposed", status: "proposed" }),
      act({ id: "l2", autonomy_level: "L2" }),
      act({ id: "undone", status: "undone" }),
    ];
    expect(feedActions(rows).map((a) => a.id)).toEqual(["new", "old"]);
  });

  it("falls back to created_at when executed_at is absent", () => {
    const rows = [
      act({ id: "a", executed_at: null, created_at: "2026-11-01T09:00:00Z" }),
      act({ id: "b", executed_at: null, created_at: "2026-11-01T10:00:00Z" }),
    ];
    expect(feedActions(rows).map((a) => a.id)).toEqual(["b", "a"]);
  });
});

describe("undoable", () => {
  it("is true inside the 24h window", () => {
    expect(undoable(act({}), NOW)).toBe(true);
  });
  it("is false once the window has passed", () => {
    expect(undoable(act({ undo_deadline: "2026-11-01T11:00:00Z" }), NOW)).toBe(false);
  });
  it("respects can_undo=false and missing deadline", () => {
    expect(undoable(act({ can_undo: false }), NOW)).toBe(false);
    expect(undoable(act({ undo_deadline: null }), NOW)).toBe(false);
  });
  it("is false for a non-executed action", () => {
    expect(undoable(act({ status: "undone" }), NOW)).toBe(false);
  });
});

describe("remainingMs / remainingLabel", () => {
  it("clamps to zero past the deadline", () => {
    expect(remainingMs(act({ undo_deadline: "2026-11-01T11:00:00Z" }), NOW)).toBe(0);
  });
  it("reports the time left", () => {
    expect(remainingMs(act({}), NOW)).toBe(23 * 3_600_000);
  });
  it("formats hours and minutes", () => {
    expect(remainingLabel(23 * 3_600_000 + 59 * 60_000)).toBe("23h 59m");
    expect(remainingLabel(9 * 60_000)).toBe("9m");
    expect(remainingLabel(0)).toBe("0m");
  });
});
